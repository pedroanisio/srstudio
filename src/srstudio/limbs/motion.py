"""Public motion records and orchestration for history-independent limb performance.

Transform interpolation, gesture requests, contact constraints and skeletal solving
have separate internal owners. Records and method hooks retain this public path;
derived join and pole caches remain per-instance and bounded.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cached_property

from . import _motion_contacts, _motion_gestures, _motion_kinematics, _motion_transforms
from ._motion_gestures import _GOALS as _GOALS
from ._motion_gestures import _blend as _blend
from ._motion_gestures import _recipe as _recipe
from ._motion_interpolation import smooth as smooth
from .errors import Diagnostic, LimbError
from .math3d import Frame, Quaternion, Vec3, bounded, number
from .model import ArmPose, ArmProfile, HandControl, HandPose, HandProfile, label
from .transitions import ActionJoin, JoinPlan, JoinWindow, prepare_join, resolve_joins, sample_join

# Preserve the supported function identity as well as the public record identities below.
smooth.__module__ = __name__

ACTIONS = (
    "rest",
    "crossed",
    "reach",
    "point",
    "present",
    "shrug",
    "wave",
    "facepalm",
    "pinch",
    "grasp",
    "release",
    "press",
    "type",
)


@dataclass(frozen=True)
class TransformKey:
    time: float
    frame: Frame
    velocity: Vec3 | None = None
    angular_velocity: Vec3 | None = None

    def __post_init__(self) -> None:
        if number(self.time, "transform key time") < 0:
            raise LimbError("transform key time must be non-negative")
        for value in (self.velocity, self.angular_velocity):
            if value is not None and not isinstance(value, Vec3):
                raise LimbError('transform key velocities must be Vec3 values')


@dataclass(frozen=True)
class TransformTrack:
    """A transform in motion seconds. Smooth mode stops at each key; continuous mode passes interior keys.

    Continuous translation uses quintic segments with shared velocity and zero acceleration at keys. Rotations
    target shared local angular velocity through spherical controls; small-arc blending is approximate. Units are
    parent units/s and local radians/s. Missing interior velocities use neighboring poses; endpoints default to zero.
    Explicit endpoint velocities describe the animated interval; outside it the nearest frame is still held.
    """

    keys: tuple[TransformKey, ...]
    interpolation: str = 'smooth'

    def __post_init__(self) -> None:
        if not self.keys or len(self.keys) > 10000:
            raise LimbError("a transform track needs one to 10000 keys")
        if any(a.time >= b.time for a, b in zip(self.keys, self.keys[1:], strict=False)):
            raise LimbError("transform key times must be strictly increasing")
        if self.interpolation not in ('smooth', 'continuous'):
            raise LimbError('transform interpolation must be smooth or continuous')
        if self.interpolation == 'smooth' and any(
            k.velocity is not None or k.angular_velocity is not None for k in self.keys
        ):
            raise LimbError('explicit key velocities require continuous interpolation')
        if self.interpolation == 'continuous':
            for i, (a, b) in enumerate(zip(self.keys, self.keys[1:], strict=False)):
                if (
                    max(self._velocities[i][1].length, self._velocities[i + 1][1].length) * (b.time - a.time) / 3
                    >= math.pi / 2
                ):
                    raise LimbError('angular velocity exceeds a spherical control arc; add keys or reduce velocity')

    @cached_property
    def _times(self) -> tuple[float, ...]:
        return tuple(key.time for key in self.keys)

    @cached_property
    def _velocities(self) -> tuple[tuple[Vec3, Vec3], ...]:
        return _motion_transforms.velocities(self)

    @classmethod
    def constant(cls, frame: Frame) -> TransformTrack:
        return cls((TransformKey(0, frame),))

    def describe_continuity(self) -> dict:
        """Versioned source-key guarantees, angular approximation and explicit endpoint hold jumps."""
        from ._continuity import describe_track

        return describe_track(self)

    def sample(self, time: float) -> Frame:
        return _motion_transforms.sample(self, time)


@dataclass(frozen=True)
class Target:
    position: Vec3
    space: str = "relative"

    def __post_init__(self) -> None:
        if self.space not in ("relative", "world"):
            raise LimbError("target space must be relative or world")


@dataclass(frozen=True)
class MotionStyle:
    """Gesture dynamics: amplitude 0..2, speed 0.25..4, and all other controls 0..1.

    Overshoot and arc shape the stroke; settling adds a fading hold wobble. Tension curls fingers and asymmetry
    offsets the gesture sideways. These controls affect motion, not a character's facial expression.
    """

    amplitude: float = 1.0
    speed: float = 1.0
    tension: float = 0.0
    overshoot: float = 0.0
    asymmetry: float = 0.0
    settling: float = 0.0
    arc: float = 0.04

    def __post_init__(self) -> None:
        bounded(self.amplitude, 0, 2, "amplitude")
        bounded(self.speed, 0.25, 4, "speed")
        for name in ("tension", "overshoot", "asymmetry", "settling", "arc"):
            bounded(getattr(self, name), 0, 1, name)


@dataclass(frozen=True)
class WordRef:
    """Identify a word by take ID and zero-based word index."""

    take: str
    index: int

    def __post_init__(self) -> None:
        label(self.take, "word take ID")
        if isinstance(self.index, bool) or not isinstance(self.index, int) or not 0 <= self.index < 1000000:
            raise LimbError("word reference needs an integer word index in 0..999999")


@dataclass(frozen=True)
class Action:
    """A named gesture in seconds, with preparation, stroke and hold fractions followed by recovery.

    Zero preparation starts smoothly from rest; ``rest`` holds the resting pose while following the root.
    """

    name: str
    start: float = 0.0
    duration: float = 1.5
    target: Target | None = None
    style: MotionStyle = MotionStyle()
    preparation: float = 0.15
    stroke: float = 0.25
    hold: float = 0.35
    control: HandControl | None = None
    pole: Vec3 | None = None

    def __post_init__(self) -> None:
        label(self.name, "action name")
        if self.name not in ACTIONS:
            raise LimbError(f"unknown action {self.name!r}; expected one of {ACTIONS}")
        if number(self.start, "action start") < 0 or number(self.duration, "action duration") <= 0:
            raise LimbError("action start must be non-negative and duration positive")
        number(self.start + self.duration, "action end")
        for n in ("preparation", "stroke", "hold"):
            bounded(getattr(self, n), 0, 1, n)
        if self.stroke <= 0 or self.preparation + self.stroke + self.hold >= 1:
            raise LimbError("gesture phases need a stroke and positive recovery time")

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def stroke_at(self) -> float:
        return self.start + (self.preparation + self.stroke) * self.duration

    @classmethod
    def on_word(cls, name: str, ref: WordRef, takes: Sequence, *, duration: float = 1.5, **options) -> Action:
        """Schedule the stroke's end at the referenced word's project time; do not also pass ``start``."""
        if "start" in options:
            raise LimbError("Action.on_word determines start from the word; do not supply start")
        matches = [take for take in takes if take.id == ref.take]
        if len(matches) != 1 or ref.index >= len(matches[0].words):
            raise LimbError(f"word reference {ref.take}:{ref.index} does not resolve uniquely")
        take = matches[0]
        word = take.words[ref.index]
        if not isinstance(word, Mapping) or "start" not in word:
            raise LimbError(f"word {ref.take}:{ref.index} has no start time")
        at = number(word["start"], "word start") + number(take.start, "take start")
        candidate = cls(name, duration=duration, **options)
        return replace(candidate, start=at - candidate.stroke_at)


@dataclass(frozen=True)
class Contact:
    name: str
    start: float
    end: float
    target: TransformTrack
    digit: str | None = None
    anchor: Frame = Frame()

    def __post_init__(self) -> None:
        label(self.name, "contact name")
        if not self.name or not 0 <= number(self.start, "contact start") < number(self.end, "contact end"):
            raise LimbError("contact needs a name and ordered non-negative times")

    def frame(self, time: float) -> Frame:
        return self.target.sample(time).compose(self.anchor)


@dataclass(frozen=True)
class Attachment:
    name: str
    attach: float
    release: float
    initial: Frame
    offset: Frame = Frame()
    tolerance: float = 1e-6

    def __post_init__(self) -> None:
        label(self.name, "attachment name")
        if not self.name or not 0 <= number(self.attach, "attach") < number(self.release, "release"):
            raise LimbError("attachment needs a name and ordered non-negative times")
        if number(self.tolerance, "attachment tolerance") < 0:
            raise LimbError("attachment tolerance must be non-negative")


@dataclass(frozen=True)
class Sample:
    time: float
    arm: ArmPose
    hand: HandPose
    control: HandControl
    action: str
    phase: str
    contacts: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class Motion:
    arm: ArmProfile
    hand: HandProfile
    actions: tuple[Action, ...] = ()
    contacts: tuple[Contact, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    root: TransformTrack = TransformTrack((TransformKey(0, Frame()),))
    reach_policy: str = "strict"
    joins: tuple[ActionJoin, ...] = ()

    def __post_init__(self) -> None:
        if len(self.actions) > 10000 or self.reach_policy not in ("strict", "clamp"):
            raise LimbError("motion has too many actions or an unknown reach policy")
        if any(a.end > b.start for a, b in zip(self.actions, self.actions[1:], strict=False)):
            raise LimbError("actions must be ordered without overlap")
        if any(a.end > b.start for a, b in zip(self.contacts, self.contacts[1:], strict=False)):
            raise LimbError("contacts must be ordered without overlap")
        # A contact locks exactly, so the hand needs a transition interval to reach it and to leave it.
        if any(a.end == b.start for a, b in zip(self.contacts, self.contacts[1:], strict=False)):
            raise LimbError("successive contacts need a transition interval between them")
        names = [a.name for a in self.attachments]
        if len(set(names)) != len(names):
            raise LimbError("prop attachment names must be unique")
        for c in self.contacts:
            if not any(a.start <= c.start < c.end <= a.end for a in self.actions):
                raise LimbError(f"contact {c.name} must lie inside one action")
            if not any(a.start < c.start < c.end < a.end for a in self.actions):
                raise LimbError(
                    f"contact {c.name} needs a transition interval after its action starts and before it ends"
                )
            if c.digit is not None and c.digit not in {d.name for d in self.hand.digits}:
                raise LimbError(f"contact names an unknown digit {c.digit}")
        _ = self._join_windows  # Validate composition before evaluating attachment acquisition.
        for a in self.attachments:
            actual = self.sample(a.attach).hand.frame.compose(a.offset)
            if actual.origin.distance(a.initial.origin) > a.tolerance:
                raise LimbError(f"prop {a.name} would jump at acquisition", code="contact")
            error = actual.rotation.inverse() * a.initial.rotation
            if 2 * math.acos(min(1, abs(error.w))) > a.tolerance:
                raise LimbError(f"prop {a.name} would rotate at acquisition", code="contact")

    def retarget(self, arm: ArmProfile, hand: HandProfile | None = None) -> Motion:
        return replace(self, arm=arm, hand=hand or self.hand)

    def describe_continuity(self) -> dict:
        """Describe source joins and held emission without sampling or certifying the whole motion."""
        from ._continuity import describe_motion

        return describe_motion(self)

    def chain(self, *after: int) -> Motion:
        """Join selected adjacent action pairs (all by default), preserving explicitly authored join windows."""
        indices = after or tuple(range(len(self.actions) - 1))
        joins = {join.after: join for join in self.joins}
        for index in indices:
            join = ActionJoin(index)
            joins.setdefault(index, join)
        return replace(self, joins=tuple(joins[index] for index in sorted(joins)))

    @cached_property
    def _join_windows(self) -> tuple[JoinWindow, ...]:
        return resolve_joins(self)

    @cached_property
    def _join_starts(self) -> tuple[float, ...]:
        return tuple(window.start for window in self._join_windows)

    @cached_property
    def _join_plans(self) -> dict[int, JoinPlan]:
        return {}

    @property
    def end(self) -> float:
        """Latest authored action, root key or attachment release; zero for an entirely static motion."""
        return max([self.root.keys[-1].time, *(a.end for a in self.actions), *(a.release for a in self.attachments)])

    def _relative(self, point: Vec3, time: float) -> Vec3:
        return _motion_gestures.relative(self, point, time)

    def _request(self, time: float) -> tuple[Vec3, HandControl, Action | None, str]:
        return _motion_gestures.request(self, time)

    def _contact_request(self, contact: Contact, time: float, control: HandControl) -> tuple[Vec3, Quaternion]:
        return _motion_contacts.request(self, contact, time, control)

    def _contact_position(self, action: Action, time: float, fallback: Vec3) -> Vec3:
        return _motion_contacts.position(self, action, time, fallback)

    def _pole_geometry(self, action: Action, time: float, goal: Vec3) -> tuple[Vec3, Vec3, float]:
        return _motion_kinematics.pole_geometry(self, action, time, goal)

    @cached_property
    def _pole_paths(self) -> dict[tuple[int, float, float], tuple[tuple[float, ...], tuple[float, ...]]]:
        # At most two transitions are retained; derived data never enters motion serialization or equality.
        return {}

    def _pole_path(self, action: Action, start: float, end: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
        return _motion_kinematics.pole_path(self, action, start, end)

    def _pole(self, action: Action | None, time: float, goal: Vec3) -> Vec3:
        return _motion_kinematics.pole(self, action, time, goal)

    def sample(self, time: float) -> Sample:
        if number(time, "sample time") < 0:
            raise LimbError("motion sample time must be non-negative")
        try:
            return self._sample(time)
        except LimbError as error:
            context: dict[str, str | int | float] = {'time': time, 'side': self.arm.side}
            for index, action in enumerate(self.actions):
                if action.start <= time < action.end:
                    context.update(action=action.name, action_index=index)
                    break
            raise error.with_context(**context) from error

    def _sample(self, time: float) -> Sample:
        index = bisect_right(self._join_starts, time) - 1
        if index >= 0:
            window = self._join_windows[index]
            if window.start < time < window.end:
                try:
                    if index not in self._join_plans:
                        plan = prepare_join(self, window)
                        if len(self._join_plans) >= 64:
                            self._join_plans.clear()
                        self._join_plans[index] = plan
                    return sample_join(self, self._join_plans[index], time)
                except LimbError as error:
                    raise error.with_context(join_after=window.after, phase='transition') from error
        return self._sample_actions(time)

    def _sample_actions(self, time: float) -> Sample:
        goal, control, action, phase = self._request(time)
        goal, orientation, local_orientation, active = _motion_contacts.resolve(self, time, goal, control, action)
        pole = self._pole(action, time, goal)
        arm, hand, control = self._pose(time, goal, control, pole, orientation, local_orientation)
        diagnostics = _motion_contacts.diagnostics(active, hand, time)
        return Sample(time, arm, hand, control, action.name if action else "rest", phase, diagnostics)

    def _pose(
        self,
        time: float,
        goal: Vec3,
        control: HandControl,
        pole: Vec3,
        orientation: Quaternion | None = None,
        local_orientation: bool = False,
    ) -> tuple[ArmPose, HandPose, HandControl]:
        return _motion_kinematics.pose(self, time, goal, control, pole, orientation, local_orientation)

    def prop_frame(self, name: str, time: float) -> Frame:
        return _motion_contacts.prop_frame(self, name, time)


def sample_motion(motion: Motion, time: float, *, track: str) -> Sample:
    """Sample a named compilation input while retaining the originating motion's error context."""
    try:
        return motion.sample(time)
    except LimbError as error:
        raise error.with_context(track=track) from error
