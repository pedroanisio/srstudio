"""Validated acting phase schedules and bounded baking through the shared channel sampler."""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import checks
from ._curves import progress
from .acting import ActingBeat, ActingRig, ChannelTiming, TransitionPolicy, _error
from .head_motion import CHANNELS, Channel, Spring
from .toon_head import Glancing

VERSION = '1.0.0'
CURVES = (
    ('linear', 'ease-in', 'ease-out', 'ease-in-out')
    + tuple(
        f'{family}-{direction}'
        for family in ('quad', 'cubic', 'quart', 'quint', 'sine', 'expo', 'circ', 'back', 'elastic', 'bounce')
        for direction in ('in', 'out', 'in-out')
    )
    + ('spring',)
)
MAX_SAMPLES = 20_000


def supported(rig: ActingRig) -> set[str]:
    result = {'expression'}
    if rig.gloss_character != 'sunny':
        result.add('gesture')
    if rig.family == 'toon':
        result.update(CHANNELS)
        if rig.head_rig is not None and isinstance(rig.head_rig.look.drawing, Glancing):
            result.add('gaze')
    return result


def describe_continuity(*, policy: bool) -> dict:
    return {
        'position': (
            'linear baked keys; zero-duration arrivals change within one scene quantum (1 microsecond)'
            if policy
            else 'linear baked keys on the score sample grid'
        ),
        'velocity': False,
        'acceleration': False,
        'scope': 'compiled numeric channels, before rig drawing and projection',
        'source_curve_derivatives_preserved': False,
        'discrete': dict(position=False, velocity=False, acceleration=False),
        'discrete_boundary': 'held drawings switch at arrival; no facial morph',
        'cuts': 'same performance source time',
    }


def describe_policy(rig: ActingRig) -> dict:
    channels = supported(rig)
    return {
        'version': VERSION,
        'score_schema': 'srstudio.acting/1.1.0',
        'curves': list(CURVES) if rig.family == 'toon' else [],
        'numeric_channels': [name for name in CHANNELS if name in channels],
        'discrete_channels': sorted(channels - set(CHANNELS)),
        'facial_morph': False,
        'continuity': describe_continuity(policy=True),
        'fields': {
            'version': {'required_in_json': True, 'value': VERSION},
            'curve': {'default': 'sine-in-out', 'requires': 'an assigned numeric channel'},
            'anticipation': {'unit': 'seconds before delayed launch', 'range': [0, 600], 'default': 0},
            'anticipation_amount': {
                'unit': 'fraction of target delta opposite the move',
                'range': [0, 1],
                'default': 0.15,
            },
            'settle': {'unit': 'seconds after arrival', 'range': [0, 600], 'default': 0},
            'overshoot': {
                'unit': 'fraction of target delta beyond arrival',
                'range': [0, 1],
                'default': 0,
                'requires': 'positive settle',
            },
            'spring': {
                'requires': 'curve=spring',
                'frequency_hz': [0.1, 20],
                'damping_ratio': [0.1, 2],
                'default': {'frequency': 3, 'damping': 0.75},
                'anticipation': 'must be zero; use policy phase',
            },
            'timing': {
                'max_items': len(CHANNELS) + 3,
                'unique_by': 'channel',
                'channel': sorted(channels),
                'requires': 'channel assigned by this beat',
                'delay': {'unit': 'seconds', 'range': [0, 600], 'default': 0},
                'duration': {'unit': 'seconds', 'range': [0, 600], 'default': 'beat.transition'},
            },
        },
        'constraints': [
            'All phases fit inside performance duration and reserve their channel until settling ends.',
            'Emotion labels follow expression arrival; speech mouth remains owned by speech or overrides.',
            'Drawings switch at arrival. Anticipation, easing and settling apply only to numeric channels.',
            'Numeric anticipation or settling requires a positive transition at scene precision.',
            'Reset phases cannot overlap active contacts or prop attachments.',
            'Whole-channel overrides retain precedence; limits apply to emitted sampled values.',
        ],
        'sampling': {'minimum_policy_hz': 240, 'spring_samples_per_cycle': 32, 'max_keys_per_channel': MAX_SAMPLES},
    }


def _bounded(value: object, path: str, maximum: float) -> None:
    if not checks.number(value) or not 0 <= value <= maximum:
        raise _error(path, value, f'a finite number in 0..{maximum}, excluding booleans')


def validate(policy: object, rig: ActingRig, assigned: set[str], path: str) -> TransitionPolicy:
    if not isinstance(policy, TransitionPolicy):
        raise _error(path, policy, 'a TransitionPolicy')
    if policy.version != VERSION:
        raise _error(path + '.version', policy.version, VERSION)
    if not isinstance(policy.curve, str) or policy.curve not in CURVES:
        raise _error(path + '.curve', policy.curve, CURVES)
    for name, maximum in (('anticipation', 600), ('settle', 600), ('anticipation_amount', 1), ('overshoot', 1)):
        _bounded(getattr(policy, name), path + '.' + name, maximum)
    if policy.overshoot and not policy.settle:
        raise _error(path + '.overshoot', policy.overshoot, 'positive settle to return to the authored target')
    if policy.spring is not None:
        spring = policy.spring
        if policy.curve != 'spring' or not isinstance(spring, Spring):
            raise _error(path + '.spring', spring, 'a Spring used only with curve=spring')
        if not 0.1 <= spring.frequency <= 20 or not 0.1 <= spring.damping <= 2 or spring.anticipation != 0:
            raise _error(path + '.spring', spring, 'frequency 0.1..20 Hz, damping 0.1..2, anticipation=0')
    if not isinstance(policy.timing, tuple) or len(policy.timing) > len(CHANNELS) + 3:
        raise _error(path + '.timing', policy.timing, 'a tuple of at most 11 ChannelTiming records')
    seen: set[str] = set()
    available = assigned & supported(rig)
    for i, timing in enumerate(policy.timing):
        where = f'{path}.timing[{i}]'
        if not isinstance(timing, ChannelTiming) or not isinstance(timing.channel, str):
            raise _error(where, timing, 'a ChannelTiming with a named channel')
        if timing.channel not in available or timing.channel in seen:
            raise _error(where + '.channel', timing.channel, {'unique_assigned_channels': sorted(available)})
        seen.add(timing.channel)
        _bounded(timing.delay, where + '.delay', 600)
        if timing.duration is not None:
            _bounded(timing.duration, where + '.duration', 600)
    if not available:
        raise _error(path, policy, 'at least one supported channel assigned by this beat')
    if not available.intersection(CHANNELS) and (
        policy.curve != 'sine-in-out'
        or policy.anticipation
        or policy.settle
        or policy.overshoot
        or policy.spring
        or policy.anticipation_amount != 0.15
    ):
        raise _error(
            path, policy, 'numeric controls on a beat assigning supported numeric channels', 'acting.unsupported'
        )
    return policy


@dataclass(frozen=True)
class Window:
    start: float
    launch: float
    arrival: float
    end: float
    policy: TransitionPolicy | None = None
    channel: Channel | None = None

    def weight(self, time: float) -> float:
        if time >= self.end:
            return 1.0
        if self.channel is not None:
            return self.channel.sample(time)
        return progress('sine-in-out', (time - self.launch) / (self.arrival - self.launch))


def schedules(beat: ActingBeat, rig: ActingRig, assigned: set[str], duration: float, path: str) -> dict[str, Window]:
    on, off = round(beat.at, 6), round(beat.at + beat.transition, 6)
    if beat.policy is None:
        return {name: Window(on, on, off, off) for name in sorted(assigned)}
    path += '.policy'
    policy = validate(beat.policy, rig, assigned, path)
    timings = {t.channel: t for t in policy.timing}
    windows = {}
    for name in sorted(assigned):
        timing = timings.get('expression' if name == 'emotion' else name)
        launch = round(beat.at + (timing.delay if timing else 0), 6)
        span = timing.duration if timing and timing.duration is not None else beat.transition
        arrival = round(launch + span, 6)
        numeric = name in CHANNELS and rig.family == 'toon'
        start = round(launch - (policy.anticipation if numeric else 0), 6)
        end = round(arrival + (policy.settle if numeric else 0), 6)
        where = f'{path}.{name}'
        if not 0 <= start <= launch <= arrival <= end < duration:
            raise _error(where, (start, launch, arrival, end), 'ordered phases wholly inside the performance')
        if numeric and arrival == launch and (policy.anticipation or policy.settle):
            raise _error(where, span, 'a positive transition at six-decimal scene precision for anticipation/settling')
        if numeric and ((policy.anticipation and start == launch) or (policy.settle and arrival == end)):
            raise _error(where, policy, 'nonzero phases resolvable at six-decimal scene precision')
        channel = None
        if numeric and arrival > launch:
            keys = [(start, 0.0)]
            if start < launch:
                keys.append((launch, -policy.anticipation_amount))
            keys.append((arrival, 1 + policy.overshoot))
            if end > arrival:
                keys.append((end, 1.0))
            channel = Channel(
                tuple(keys),
                spring=(policy.spring or Spring(3, 0.75)) if policy.curve == 'spring' else None,
                curve='linear' if policy.curve == 'spring' else policy.curve,
            )
        windows[name] = Window(start, launch, arrival, end, policy, channel)
    return windows


@dataclass(frozen=True)
class NumericEvent:
    window: Window
    target: float | None


def compile_channel(base: Channel, events: list[NumericEvent], duration: float, rate: int) -> Channel:
    """Emit bounded linear samples; the declared contract is the bake, not unsampled physics."""
    times = {round(i / rate, 6) for i in range(math.ceil(duration * rate))} | {duration}
    times.update(t for t, _ in base.keys)
    for event in events:
        w = event.window
        times.update((w.start, w.launch, w.arrival, w.end))
        if w.policy is not None:
            if w.start == w.end and w.start > 0:
                # Keep an instantaneous arrival from becoming a ramp over the preceding frame.
                times.add(round(w.start - 0.000001, 6))
            frequency = w.channel.spring.frequency if w.channel and w.channel.spring else 0
            hz = max(240, math.ceil(32 * frequency))
            count = math.ceil((w.end - w.start) * hz)
            if len(times) + count > MAX_SAMPLES:
                raise _error(
                    'policy.samples',
                    len(times) + count,
                    f'at most {MAX_SAMPLES} candidate keys per channel',
                    'acting.budget',
                )
            times.update(round(w.start + i / hz, 6) for i in range(count))
        if len(times) > MAX_SAMPLES:
            raise _error('policy.samples', len(times), f'at most {MAX_SAMPLES} keys per channel', 'acting.budget')
    keys, index = [], -1
    for t in sorted(times):
        while index + 1 < len(events) and events[index + 1].window.start <= t:
            index += 1
        if index < 0:
            value = base.sample(t)
        else:
            event = events[index]
            source = events[index - 1].target if index else None
            a = base.sample(t) if source is None else source
            b = base.sample(t) if event.target is None else event.target
            value = a + (b - a) * event.window.weight(t)
        keys.append((t, round(value, 4)))
    return Channel(tuple(keys))
