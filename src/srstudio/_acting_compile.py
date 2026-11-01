"""Bounded acting compilation; public records and random-access views live in acting."""

from __future__ import annotations

import math
from dataclasses import fields, replace
from typing import Any

from sr_core.scene import Scene

from . import checks, lipsync
from . import head_motion as hm
from ._curves import progress
from .acting import (
    ActingBeat,
    ActingRig,
    ActingScore,
    Emotion,
    Expression,
    HeadTarget,
    Overrides,
    PerformancePlan,
    SpokenLine,
    _error,
    _held,
)
from .canvas import Canvas
from .character_clips import GlossClip, ToonClip, _check
from .head_motion import CHANNELS, GAZES, Channel, HeadPlan
from .limbs.integration import LimbTrack
from .toon import Pose
from .toon_head import HeadRig
from .voice import Alignment

MAX_EVENTS = 1000
MAX_SAMPLES = 20_000


def _seq(value, path, limit=MAX_EVENTS):
    if not isinstance(value, tuple) or len(value) > limit:
        raise _error(path, value, f'a tuple with at most {limit} entries')


def _time(value, path, duration, endpoint=False):
    if not checks.number(value) or not 0 <= value or (value > duration if endpoint else value >= duration):
        raise _error(path, value, f'a finite second in 0..{duration}')


def _track(value, path, duration, kind=str):
    _seq(value, path, MAX_SAMPLES)
    last = -1.0
    for i, row in enumerate(value):
        if not isinstance(row, tuple) or len(row) != 2 or not isinstance(row[1], kind):
            raise _error(f'{path}[{i}]', row, f'a (second, {kind.__name__}) pair')
        _time(row[0], f'{path}[{i}].time', duration)
        if round(row[0], 6) <= last:
            raise _error(path, value, 'strictly increasing seconds at scene precision')
        last = round(row[0], 6)


def _clip(rig, expressions, gestures, mouths=(), head=None, limbs=()):
    if rig.family == 'gloss':
        return GlossClip(
            rig.gloss_character,
            talk=mouths,
            face=tuple((t, e.eyes) for t, e in expressions),
            pose=tuple((t, g) for t, g in gestures if g is not None),
            limbs=limbs,
        )
    times = sorted({t for t, _ in expressions} | {t for t, _ in gestures})
    poses = tuple(Pose(t, _held(expressions, t).eyes, _held(expressions, t).mouth, _held(gestures, t)) for t in times)
    return ToonClip(rig.head_rig, poses, head=head or HeadPlan.still(), mouths=mouths)


def _expression(rig, expression, previous):
    if not isinstance(expression, Expression) or not isinstance(expression.eyes, str):
        raise _error('expression', expression, 'an Expression with a named eye/face state')
    if rig.family == 'gloss' and expression.mouth is not None:
        raise _error('expression.mouth', expression.mouth, 'speech mouth tracks for Gloss', 'acting.unsupported')
    return Expression(expression.eyes, previous.mouth if expression.mouth is None else expression.mouth)


def _speech(lines, path, duration):
    _seq(lines, path)
    result, mouth = [], {}
    previous = 0.0
    for i, line in enumerate(lines):
        where = f'{path}[{i}]'
        if not isinstance(line, SpokenLine) or not isinstance(line.alignment, Alignment):
            raise _error(where, line, 'a SpokenLine with typed Alignment')
        _time(line.at, f'{where}.at', duration)
        _seq(line.alignment.characters, f'{where}.characters', MAX_SAMPLES)
        _seq(line.alignment.starts, f'{where}.starts', MAX_SAMPLES)
        _seq(line.alignment.ends, f'{where}.ends', MAX_SAMPLES)
        alignment = Alignment.parse(line.alignment.to_json(), where)
        end = max(alignment.ends, default=0)
        if end <= 0 or line.at < previous or line.at + end > duration:
            raise _error(where, line.at, 'non-overlapping positive-length speech inside the performance')
        _seq(line.levels, f'{where}.levels', 60_000)
        if len(line.levels) < math.ceil(end * hm.LOUD_RATE - 1e-9) or not all(checks.number(x) for x in line.levels):
            raise _error(f'{where}.levels', line.levels, 'finite measured dB samples covering the alignment at 100 Hz')
        result.append(hm.Speech(line.at, hm.words_of(alignment, line.at), line.levels))
        phones = [
            dict(c=c, start=a, end=b)
            for c, a, b in zip(alignment.characters, alignment.starts, alignment.ends, strict=True)
        ]
        for t, state in lipsync.phoneme_states(phones, end, style=lipsync.SPEECH_MOUTH):
            mouth[round(line.at + t, 6)] = state
        mouth[round(line.at + end, 6)] = 'closed'
        previous = line.at + end
    return tuple(result), tuple(sorted(mouth.items()))


def _numeric(base: Channel, events, duration, rate):
    if not events:
        return base
    times = {round(i / rate, 6) for i in range(math.ceil(duration * rate))} | {duration}
    times.update(t for t, _ in base.keys)
    times.update(t for on, off, _ in events for t in (on, off))
    if len(times) > MAX_SAMPLES:
        raise _error('head', len(times), f'at most {MAX_SAMPLES} sampled keys', 'acting.budget')
    keys, index = [], -1
    for t in sorted(times):
        while index + 1 < len(events) and events[index + 1][0] <= t:
            index += 1
        if index < 0:
            value = base.sample(t)
        else:
            on, off, target = events[index]
            source = events[index - 1][2] if index else None
            a = base.sample(t) if source is None else source
            b = base.sample(t) if target is None else target
            weight = progress('sine-in-out', (t - on) / (off - on)) if t < off else 1.0
            value = a + (b - a) * weight
        keys.append((t, round(value, 4)))
    return Channel(tuple(keys))


def _append(track, time, value):
    if track and track[-1][0] == time:
        track[-1] = (time, value)
    elif not track or track[-1][1] != value:
        track.append((time, value))


def _follow(base: HeadPlan, gaze, rig: ActingRig, duration: float, rate: int) -> HeadPlan:
    """Authored eye holds lead horizontal head follow; dense holds shorten its arrival."""
    assert rig.head_rig is not None
    HeadPlan(gaze=tuple(gaze)).check_gaze()
    starts = [min(duration, round(time + 0.08, 6)) for time, _ in gaze]
    channels = {}
    for channel, amount in (('turn', rig.head_rig.style.glance_turn), ('face_x', rig.head_rig.style.glance_face)):
        events = []
        for i, ((_, name), on) in enumerate(zip(gaze, starts, strict=True)):
            if on >= duration:
                continue
            off = min(duration, round(on + 0.25, 6), starts[i + 1] if i + 1 < len(starts) else duration)
            events.append((on, off, amount * GAZES[name][0] / GAZES['right'][0]))
        channels[channel] = _numeric(getattr(base, channel), events, duration, rate)
    return replace(base, **channels, gaze=tuple(gaze))


def compile_score(rig: ActingRig, score: ActingScore) -> PerformancePlan:
    if not isinstance(rig, ActingRig) or not isinstance(score, ActingScore):
        raise _error('rig/score', None, 'typed ActingRig and ActingScore records')
    if not checks.number(score.duration) or not 1e-4 <= score.duration <= 600:
        raise _error('duration', score.duration, 'a finite duration in 0.0001..600 seconds')
    if type(score.sample_rate) is not int or not 1 <= score.sample_rate <= 120:
        raise _error('sample_rate', score.sample_rate, 'an integer in 1..120')
    if math.ceil(score.duration * score.sample_rate) + 1 > MAX_SAMPLES:
        raise _error('sample_rate', score.sample_rate, f'duration * sample_rate + 1 <= {MAX_SAMPLES}', 'acting.budget')
    if type(score.seed) is not int or not 0 <= score.seed <= 2**31 - 1 or type(score.idle) is not bool:
        raise _error('seed/idle', (score.seed, score.idle), 'an integer seed in 0..2^31-1 and a boolean idle flag')
    if rig.family not in ('toon', 'gloss') or (rig.family == 'toon') != (rig.head_rig is not None):
        raise _error('rig', rig, 'a Toon head rig or a Gloss character profile')
    if not isinstance(rig.name, str) or not 1 <= len(rig.name) <= 128:
        raise _error('rig.name', rig.name, 'a name of 1..128 characters')
    if rig.family == 'toon' and (not isinstance(rig.head_rig, HeadRig) or rig.gloss_character is not None):
        raise _error('rig.head_rig', rig.head_rig, 'a typed HeadRig, without a Gloss character')
    if rig.family == 'gloss' and rig.gloss_character not in ('nadia', 'gus', 'tamsin', 'sunny'):
        raise _error('rig.gloss_character', rig.gloss_character, 'a supported Gloss character')
    _seq(rig.emotions, 'rig.emotions')
    if any(not isinstance(m, Emotion) or not isinstance(m.name, str) or not m.name for m in rig.emotions):
        raise _error('rig.emotions', rig.emotions, 'named Emotion records')
    if any(not isinstance(m.expression, Expression) for m in rig.emotions):
        raise _error('rig.emotions', rig.emotions, 'typed Expressions')
    moods = {m.name: m for m in rig.emotions}
    if 'neutral' not in moods or len(moods) != len(rig.emotions):
        raise _error('rig.emotions', rig.emotions, 'unique emotions including neutral')
    duration = score.duration
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps=str(score.sample_rate), duration=duration)
    cv = Canvas(scene, font_asset=None)
    neutral = moods['neutral']
    for mood in rig.emotions:
        expression = _expression(rig, mood.expression, neutral.expression)
        _check(cv, _clip(rig, ((0, expression),), ((0, mood.gesture),)), duration)
        moods[mood.name] = replace(mood, expression=expression)
    _seq(score.beats, 'beats')
    overrides = score.overrides
    if not isinstance(overrides, Overrides):
        raise _error('overrides', overrides, 'typed Overrides')
    for name, kind in (('expression', Expression), ('gesture', str), ('gaze', str), ('mouth', str)):
        value = getattr(overrides, name)
        if value is not None:
            _track(value, f'overrides.{name}', duration, kind)
    if overrides.head is not None and not isinstance(overrides.head, HeadPlan):
        raise _error('overrides.head', overrides.head, 'a HeadPlan')
    if overrides.head is not None and overrides.gaze is not None:
        raise _error('overrides', None, 'no conflict: HeadPlan already owns gaze', 'acting.conflict')
    _seq(overrides.limbs, 'overrides.limbs', 2)
    if any(not isinstance(track, LimbTrack) for track in overrides.limbs):
        raise _error('overrides.limbs', overrides.limbs, 'typed LimbTracks')
    if overrides.limbs and (rig.family != 'gloss' or rig.gloss_character == 'sunny'):
        raise _error('overrides.limbs', rig.name, 'a Gloss guest supporting replacement limbs', 'acting.unsupported')
    limbs = tuple(
        replace(track, options=replace(track.options, fps=track.options.fps or score.sample_rate))
        for track in overrides.limbs
    )
    if limbs and (
        overrides.gesture is not None or any(isinstance(b, ActingBeat) and b.gesture is not None for b in score.beats)
    ):
        raise _error('gesture', None, 'no conflict with explicit limb ownership', 'acting.conflict')
    speeches, mouths = _speech(score.speech, 'speech', duration)
    heard, _ = _speech(score.heard, 'heard', duration)
    if rig.family == 'gloss' and (heard or not score.idle or overrides.head is not None or overrides.gaze is not None):
        raise _error('head/gaze/idle/heard', rig.name, 'a rig with authored head controls', 'acting.unsupported')
    base = None
    directed_gaze = overrides.gaze is not None or any(
        isinstance(b, ActingBeat) and (b.gaze is not None or b.reset) for b in score.beats
    )
    if rig.head_rig is not None:
        style = replace(rig.head_rig.style, seed=rig.head_rig.style.seed + score.seed)
        if not score.idle:
            style = replace(style, idle_roll=0, idle_px=0, glance_turn=0, glance_face=0, avert=0)
        if directed_gaze:
            style = replace(style, glance_turn=0, glance_face=0, avert=0)
        base = hm.plan(style, speeches, duration, heard=heard)
        if not score.idle or directed_gaze:
            base = replace(base, gaze=())
    emotion_keys = [(0.0, 'neutral')]
    expressions = [(0.0, neutral.expression)]
    gestures = [(0.0, neutral.gesture)]
    gaze: list[tuple[float, str]] = []
    numeric: dict[str, list[tuple[float, float, float | None]]] = {name: [] for name in CHANNELS}
    busy: dict[str, float] = {}
    previous = -1.0
    for index, beat in enumerate(score.beats):
        path = f'beats[{index}]'
        if not isinstance(beat, ActingBeat):
            raise _error(path, beat, 'an ActingBeat')
        _time(beat.at, f'{path}.at', duration)
        if round(beat.at, 6) <= previous:
            raise _error(path, beat.at, 'strictly ordered beats without a timestamp conflict', 'acting.conflict')
        previous = round(beat.at, 6)
        if not checks.number(beat.transition) or beat.transition < 0 or beat.at + beat.transition >= duration:
            raise _error(
                f'{path}.transition', beat.transition, 'a nonnegative transition arriving before the performance ends'
            )
        if type(beat.reset) is not bool or (beat.head is not None and not isinstance(beat.head, HeadTarget)):
            raise _error(path, beat, 'a boolean reset and an optional HeadTarget')
        if rig.family == 'gloss' and (beat.head is not None or beat.gaze is not None or beat.breath is not None):
            raise _error(path, rig.name, 'a rig supporting head, gaze and breath controls', 'acting.unsupported')
        if beat.reset and any(
            c.start + t.options.offset <= beat.at < c.end + t.options.offset for t in limbs for c in t.motion.contacts
        ):
            raise _error(path, beat.at, 'explicit contact release before a reset', 'acting.conflict')
        if beat.reset and any(
            a.attach + t.options.offset <= beat.at < a.release + t.options.offset
            for t in limbs
            for a in t.motion.attachments
        ):
            raise _error(path, beat.at, 'explicit prop release before a reset', 'acting.conflict')
        on, off = round(beat.at, 6), round(beat.at + beat.transition, 6)
        assignments: dict[str, Any] = {}
        if beat.reset:
            assignments.update(emotion='neutral', expression=neutral.expression, gesture=neutral.gesture, gaze='ahead')
            for name in CHANNELS:
                assignments[name] = None
        if beat.emotion is not None:
            if not isinstance(beat.emotion, str) or beat.emotion not in moods:
                raise _error(f'{path}.emotion', beat.emotion, tuple(moods))
            mood = moods[beat.emotion]
            assignments.update(emotion=beat.emotion, expression=mood.expression, gesture=mood.gesture)
        if beat.expression is not None:
            assignments['expression'] = _expression(
                rig, beat.expression, assignments.get('expression', expressions[-1][1])
            )
        if beat.gesture is not None:
            assignments['gesture'] = beat.gesture
        if beat.gaze is not None:
            if not isinstance(beat.gaze, str) or beat.gaze not in GAZES:
                raise _error(f'{path}.gaze', beat.gaze, tuple(GAZES))
            assignments['gaze'] = beat.gaze
        if beat.head is not None:
            assignments.update(
                (f.name, getattr(beat.head, f.name))
                for f in fields(beat.head)
                if getattr(beat.head, f.name) is not None
            )
        if beat.breath is not None:
            if not checks.number(beat.breath) or not 0 <= beat.breath <= 1:
                raise _error(f'{path}.breath', beat.breath, 'a normalized expansion in 0..1')
            assignments['breath'] = beat.breath
        for name, value in assignments.items():
            if name in busy and on < busy[name]:
                raise _error(path, on, f'no overlap with the pending {name} transition', 'acting.conflict')
            busy[name] = off
            if name in numeric:
                if value is not None and not checks.number(value):
                    raise _error(f'{path}.head.{name}', value, 'a finite head target')
                if value is not None and rig.head_rig is not None and abs(value) > hm.limit(rig.head_rig.style, name):
                    raise _error(
                        f'{path}.head.{name}', value, f'a target inside +/-{hm.limit(rig.head_rig.style, name)}'
                    )
                numeric[name].append((on, off, value))
            else:
                _append(
                    {'emotion': emotion_keys, 'expression': expressions, 'gesture': gestures, 'gaze': gaze}[name],
                    off,
                    value,
                )
        # Validate authored choices even if a whole-channel override will replace their output.
        _check(cv, _clip(rig, ((0, expressions[-1][1]),), ((0, gestures[-1][1]),)), duration)
    owners = {
        'expression': 'beats',
        'gesture': 'beats',
        'mouth': 'speech',
        'head': 'procedural/beats',
        'gaze': 'procedural/beats',
    }
    if overrides.expression is not None:
        expressions = [(0.0, neutral.expression)]
        for t, e in overrides.expression:
            _append(expressions, t, _expression(rig, e, expressions[-1][1]))
        owners['expression'] = 'override'
    if overrides.gesture is not None:
        gestures = [(0.0, neutral.gesture)]
        for t, name in overrides.gesture:
            _append(gestures, t, name)
        owners['gesture'] = 'override'
    if limbs:
        gestures = [(0.0, None)]
        owners['gesture'] = 'limbs'
    head = None
    if base is not None:
        if directed_gaze:
            chosen = [(0.0, 'ahead')]
            for t, name in gaze if overrides.gaze is None else overrides.gaze:
                _append(chosen, t, name)
            base = _follow(base, chosen, rig, duration, score.sample_rate)
        head = replace(
            base,
            **{name: _numeric(getattr(base, name), numeric[name], duration, score.sample_rate) for name in CHANNELS},
        )
        if overrides.gaze is not None:
            owners['gaze'] = 'override'
        if overrides.head is not None:
            head = overrides.head
            owners['head'] = owners['gaze'] = 'override'
        assert rig.head_rig is not None
        head.check_bounds(rig.head_rig.style)
    mouth_keys = [(0.0, 'closed')]
    for t, name in mouths if overrides.mouth is None else overrides.mouth:
        _append(mouth_keys, t, name)
    if overrides.mouth is not None:
        owners['mouth'] = 'override'
    clip = _clip(
        rig,
        tuple(expressions),
        tuple(gestures),
        tuple((t, name) for t, name in mouth_keys if t < duration),
        head,
        limbs,
    )
    _check(cv, clip, duration)
    return PerformancePlan(
        rig,
        duration,
        clip,
        tuple(emotion_keys),
        tuple(expressions),
        tuple(gestures),
        tuple(mouth_keys),
        head,
        limbs,
        tuple(owners.items()),
    )
