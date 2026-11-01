"""Explicit, history-independent joins between adjacent gestures, with checked spatial poses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import LimbError
from .math3d import Frame, Quaternion, Vec3, number
from .model import HandControl, HandProfile

if TYPE_CHECKING:
    from .motion import Motion, Sample, TransformTrack


@dataclass(frozen=True)
class ActionJoin:
    """Replace recovery/preparation between action ``after`` and the following action.

    Default endpoints are the first action's end of hold and the next action's stroke time. Explicit start/end
    use motion seconds, stay inside their respective actions, and cannot replace an active contact. The source
    pose and its incoming/outgoing velocity determine each boundary; no playback state is carried between calls.
    """

    after: int
    start: float | None = None
    end: float | None = None

    def __post_init__(self) -> None:
        if type(self.after) is not int or not 0 <= self.after < 9999:
            raise LimbError('join after must be an action index in 0..9998', code='join.index')
        for name in ('start', 'end'):
            value = getattr(self, name)
            if value is not None and number(value, f'join {name}') < 0:
                raise LimbError('join times must be non-negative', code='join.time')
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise LimbError('join start must precede end', code='join.time')


@dataclass(frozen=True)
class JoinWindow:
    after: int
    start: float
    end: float


def resolve_joins(motion: Motion) -> tuple[JoinWindow, ...]:
    if (
        not isinstance(motion.joins, tuple)
        or len(motion.joins) > 9999
        or any(not isinstance(join, ActionJoin) for join in motion.joins)
    ):
        raise LimbError('joins must be a tuple of at most 9999 ActionJoins', code='join.invalid')
    windows: list[JoinWindow] = []
    contact_index = 0
    for join in motion.joins:
        if join.after + 1 >= len(motion.actions):
            raise LimbError('join needs an action and its successor', code='join.index', context={'after': join.after})
        a, b = motion.actions[join.after : join.after + 2]
        start = join.start if join.start is not None else a.start + a.duration * (a.preparation + a.stroke + a.hold)
        end = join.end if join.end is not None else b.stroke_at
        if not (a.start <= start < a.end and b.start < end <= b.end):
            raise LimbError(
                'join endpoints must lie inside the adjacent actions',
                code='join.time',
                context={'after': join.after, 'start': start, 'end': end},
            )
        if windows and (join.after <= windows[-1].after or start < windows[-1].end):
            raise LimbError('joins must be ordered, unique, and cannot overlap', code='join.overlap')
        # Both sequences are ordered. Scan contacts once even when chaining a long action sequence.
        while contact_index < len(motion.contacts) and motion.contacts[contact_index].end <= start:
            contact_index += 1
        if contact_index < len(motion.contacts) and motion.contacts[contact_index].start < end:
            contact = motion.contacts[contact_index]
            raise LimbError(
                f'join would replace active contact {contact.name!r}; end/start the join at contact boundaries',
                code='join.contact',
                context={'after': join.after, 'contact': contact.name},
            )
        windows.append(JoinWindow(join.after, start, end))
    return tuple(windows)


def _controls(hand: HandProfile, control: HandControl) -> tuple[float, ...]:
    """Canonical effective joint angles remove differences between curl and explicit override representations."""
    values = [control.curl, control.spread, control.opposition, control.cup]
    curls, joints = dict(control.curls), dict(control.joints)
    for digit in hand.digits:
        maximum = digit.max_flex or tuple(1.3 if i < 2 else 0.9 for i in range(len(digit.lengths)))
        values.extend(joints.get(digit.name, tuple(curls.get(digit.name, control.curl) * a for a in maximum)))
    return tuple(values)


def _control(hand: HandProfile, values: tuple[float, ...]) -> HandControl:
    index = 4
    joints = []
    for digit in hand.digits:
        end = index + len(digit.lengths)
        joints.append((digit.name, values[index:end]))
        index = end
    return HandControl(curl=values[0], spread=values[1], opposition=values[2], cup=values[3], joints=tuple(joints))


@dataclass(frozen=True)
class _Boundary:
    sample: Sample
    velocity: Vec3
    hand_velocity: Vec3
    guide_velocity: Vec3
    controls: tuple[float, ...]
    derivatives: tuple[float, ...]


def _angular(q: Quaternion, q1: Quaternion, q2: Quaternion, denominator: float) -> Vec3:
    return ((q.inverse() * q1).rotation_vector * 4 - (q.inverse() * q2).rotation_vector) / denominator


def _boundary(motion: Motion, window: JoinWindow, at: float, direction: int) -> _Boundary:
    a, b = motion.actions[window.after : window.after + 2]
    h = min(1e-4, a.duration * 1e-4, b.duration * 1e-4, (window.end - window.start) * 1e-4)
    if direction < 0:
        if at == 0:
            direction = 1
        else:
            h = min(h, at / 2)
    if h <= 0 or at + direction * h == at:
        raise LimbError('join boundary velocity cannot be resolved at this clock precision', code='join.time')
    # One-sided second-order differences use the portion of the source motion preserved outside the join.
    s0, s1, s2 = (motion._sample_actions(at + direction * h * i) for i in range(3))
    denominator = 2 * direction * h
    c0, c1, c2 = (_controls(motion.hand, s.control) for s in (s0, s1, s2))
    return _Boundary(
        s0,
        ((s1.arm.wrist - s0.arm.wrist) * 4 - (s2.arm.wrist - s0.arm.wrist)) / denominator,
        _angular(s0.hand.frame.rotation, s1.hand.frame.rotation, s2.hand.frame.rotation, denominator),
        _angular(s0.arm.frame.rotation, s1.arm.frame.rotation, s2.arm.frame.rotation, denominator),
        c0,
        tuple((4 * (y - x) - (z - x)) / denominator for x, y, z in zip(c0, c1, c2, strict=True)),
    )


@dataclass(frozen=True)
class JoinPlan:
    window: JoinWindow
    wrist: TransformTrack
    guide: TransformTrack
    first: _Boundary
    last: _Boundary


def prepare_join(motion: Motion, window: JoinWindow) -> JoinPlan:
    from .motion import TransformKey, TransformTrack

    a, b = _boundary(motion, window, window.start, -1), _boundary(motion, window, window.end, 1)
    wrist = TransformTrack(
        (
            TransformKey(window.start, a.sample.hand.frame, a.velocity, a.hand_velocity),
            TransformKey(window.end, b.sample.hand.frame, b.velocity, b.hand_velocity),
        ),
        interpolation='continuous',
    )
    guide = TransformTrack(
        (
            TransformKey(window.start, Frame(rotation=a.sample.arm.frame.rotation), angular_velocity=a.guide_velocity),
            TransformKey(window.end, Frame(rotation=b.sample.arm.frame.rotation), angular_velocity=b.guide_velocity),
        ),
        interpolation='continuous',
    )
    return JoinPlan(window, wrist, guide, a, b)


def sample_join(motion: Motion, plan: JoinPlan, time: float) -> Sample:
    from .motion import Sample, smooth

    window = plan.window
    span = window.end - window.start
    u = (time - window.start) / span
    s, ta, tb = smooth(u), u - 6 * u**3 + 8 * u**4 - 3 * u**5, -4 * u**3 + 7 * u**4 - 3 * u**5
    values = tuple(
        a + (b - a) * s + span * (va * ta + vb * tb)
        for a, b, va, vb in zip(
            plan.first.controls, plan.last.controls, plan.first.derivatives, plan.last.derivatives, strict=True
        )
    )
    control = _control(motion.hand, values)
    wrist = plan.wrist.sample(time)
    shoulder = motion.root.sample(time).point(motion.arm.shoulder)
    direction = (wrist.origin - shoulder).unit()
    sign = 1 if motion.arm.side == 'right' else -1
    hinge = plan.guide.sample(time).rotation.rotate(Vec3(0, 0, -sign))
    bend = hinge.cross(direction)
    if bend.length < 1e-8:
        raise LimbError(
            'join has an ambiguous elbow plane; choose another join window or an intermediate action',
            code='join.geometry',
        )
    arm, hand, control = motion._pose(time, wrist.origin, control, shoulder + bend, wrist.rotation)
    return Sample(time, arm, hand, control, motion.actions[window.after + 1].name, 'transition')
