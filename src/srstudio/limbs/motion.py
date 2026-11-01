"""History-independent gestures, word timing, moving contacts and explicit prop attachment lifetimes."""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace
from functools import cached_property

from .constraints import hand_pose, reach
from .errors import Diagnostic, LimbError
from .math3d import Frame, Quaternion, Vec3, bounded, number
from .model import ArmPose, ArmProfile, HandControl, HandPose, HandProfile, label

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


def smooth(value: float) -> float:
    """Minimum-jerk unit interpolation; zero velocity and acceleration at both ends."""
    u = min(1.0, max(0.0, value))
    # Rounding in the polynomial can exceed 1 within a few ulps of u=1; the range is [0, 1] by contract.
    return min(1.0, u * u * u * (10 + u * (-15 + 6 * u)))


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
    use spherical cubic Bezier segments with shared local angular velocity. Velocity units are parent units/s and
    local radians/s. Missing interior velocities use neighboring poses; endpoint velocities default to zero.
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
        result = []
        for i, key in enumerate(self.keys):
            linear, angular = Vec3(), Vec3()
            if 0 < i < len(self.keys) - 1:
                before, after = self.keys[i - 1], self.keys[i + 1]
                span = after.time - before.time
                linear = (after.frame.origin - before.frame.origin) / span
                q = key.frame.rotation.inverse()
                angular = (
                    (q * after.frame.rotation).rotation_vector - (q * before.frame.rotation).rotation_vector
                ) / span
            result.append(
                (
                    key.velocity if key.velocity is not None else linear,
                    key.angular_velocity if key.angular_velocity is not None else angular,
                )
            )
        return tuple(result)

    @classmethod
    def constant(cls, frame: Frame) -> TransformTrack:
        return cls((TransformKey(0, frame),))

    def sample(self, time: float) -> Frame:
        number(time, "sample time")
        if time <= self.keys[0].time:
            return self.keys[0].frame
        if time >= self.keys[-1].time:
            return self.keys[-1].frame
        i = bisect_right(self._times, time) - 1
        a, b = self.keys[i], self.keys[i + 1]
        span = b.time - a.time
        u = (time - a.time) / span
        if self.interpolation == 'smooth':
            u = smooth(u)
            return Frame(a.frame.origin.lerp(b.frame.origin, u), a.frame.rotation.slerp(b.frame.rotation, u))
        va, wa = self._velocities[i]
        vb, wb = self._velocities[i + 1]
        origin = (
            a.frame.origin.lerp(b.frame.origin, smooth(u))
            + va * (span * (u - 6 * u**3 + 8 * u**4 - 3 * u**5))
            + vb * (span * (-4 * u**3 + 7 * u**4 - 3 * u**5))
        )
        q0, q3 = a.frame.rotation, b.frame.rotation
        q1 = q0 * Quaternion.from_rotation_vector(wa * (span / 3))
        q2 = q3 * Quaternion.from_rotation_vector(wb * (-span / 3))
        q01, q12, q23 = q0.slerp(q1, u), q1.slerp(q2, u), q2.slerp(q3, u)
        rotation = q01.slerp(q12, u).slerp(q12.slerp(q23, u), u)
        return Frame(origin, rotation)


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


def _blend(a: HandControl, b: HandControl, u: float, hand: HandProfile) -> HandControl:
    values = {
        f.name: getattr(a, f.name) + (getattr(b, f.name) - getattr(a, f.name)) * u
        for f in fields(HandControl)
        if f.name not in ("curls", "joints")
    }
    ac, bc = dict(a.curls), dict(b.curls)
    names = sorted(ac.keys() | bc.keys())
    values["curls"] = tuple(
        (name, ac.get(name, a.curl) + (bc.get(name, b.curl) - ac.get(name, a.curl)) * u) for name in names
    )
    aj, bj = dict(a.joints), dict(b.joints)
    if aj or bj:
        anatomy = {d.name: d for d in hand.digits}
        if not (aj.keys() | bj.keys()) <= anatomy.keys():
            raise LimbError("joint overrides name an absent digit")
        joints = []
        for n in sorted(aj.keys() | bj.keys()):
            digit = anatomy[n]
            maximum = digit.max_flex or tuple(1.3 if i < 2 else 0.9 for i in range(len(digit.lengths)))
            first = aj.get(n, tuple(ac.get(n, a.curl) * angle for angle in maximum))
            last = bj.get(n, tuple(bc.get(n, b.curl) * angle for angle in maximum))
            if len(first) != len(maximum) or len(last) != len(maximum):
                raise LimbError("joint overrides must match the hand topology")
            joints.append((n, tuple(x + (y - x) * u for x, y in zip(first, last, strict=True))))
        values["joints"] = tuple(joints)
    return HandControl(**values)


def _recipe(name: str, hand: HandProfile, time: float) -> HandControl:
    finger = next((d.name for d in hand.digits if not d.thumb), hand.digits[0].name)
    if name in ("point", "press"):
        return HandControl(curl=0.75, curls=((finger, 0),), opposition=0.3)
    if name == "crossed":
        return HandControl(curl=0.55, cup=0.1, opposition=0.3)
    if name in ("grasp", "pinch"):
        return HandControl(curl=0.65 if name == "grasp" else 0.5, cup=0.5, opposition=0.85)
    if name in ("present", "shrug"):
        return HandControl(curl=0.08, spread=0.35, forearm_twist=0.9)
    if name == "wave":
        return HandControl(curl=0.08, spread=0.5, wrist_deviation=0.35 * math.sin(time * 12))
    if name == "facepalm":
        return HandControl(curl=0.08, spread=0.12, cup=0.3)
    if name == "type":
        return HandControl(curl=0.45, curls=((finger, 0.3 + 0.2 * math.sin(time * 25)),))
    if name == "release":
        return HandControl(curl=0, spread=0.25)
    return HandControl()


_GOALS = {
    "rest": Vec3(0.18, 0.68, 0),
    "crossed": Vec3(-0.4, 0.26, 0.1),
    "reach": Vec3(0.55, 0.42, -0.2),
    "point": Vec3(0.72, 0.15, -0.18),
    "present": Vec3(0.55, 0.3, 0.1),
    "shrug": Vec3(0.48, -0.10, 0.05),
    "wave": Vec3(0.40, -0.40, 0.05),
    "facepalm": Vec3(0.08, -0.28, 0.24),
    "pinch": Vec3(0.45, 0.30, 0.1),
    "grasp": Vec3(0.50, 0.32, -0.1),
    "release": Vec3(0.50, 0.32, -0.1),
    "press": Vec3(0.6, 0.4, -0.2),
    "type": Vec3(0.45, 0.55, -0.1),
}


@dataclass(frozen=True)
class Motion:
    arm: ArmProfile
    hand: HandProfile
    actions: tuple[Action, ...] = ()
    contacts: tuple[Contact, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    root: TransformTrack = TransformTrack((TransformKey(0, Frame()),))
    reach_policy: str = "strict"

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
        for a in self.attachments:
            actual = self.sample(a.attach).hand.frame.compose(a.offset)
            if actual.origin.distance(a.initial.origin) > a.tolerance:
                raise LimbError(f"prop {a.name} would jump at acquisition", code="contact")
            error = actual.rotation.inverse() * a.initial.rotation
            if 2 * math.acos(min(1, abs(error.w))) > a.tolerance:
                raise LimbError(f"prop {a.name} would rotate at acquisition", code="contact")

    def retarget(self, arm: ArmProfile, hand: HandProfile | None = None) -> Motion:
        return replace(self, arm=arm, hand=hand or self.hand)

    @property
    def end(self) -> float:
        """Latest authored action, root key or attachment release; zero for an entirely static motion."""
        return max([self.root.keys[-1].time, *(a.end for a in self.actions), *(a.release for a in self.attachments)])

    def _relative(self, point: Vec3, time: float) -> Vec3:
        root = self.root.sample(time)
        v = point.mirror() if self.arm.side == "left" else point
        return root.point(self.arm.shoulder) + root.rotation.rotate(v * self.arm.length)

    def _request(self, time: float) -> tuple[Vec3, HandControl, Action | None, str]:
        rest = self._relative(_GOALS["rest"], time)
        action = next((a for a in self.actions if a.start <= time < a.end), None)
        if action is None:
            return rest, HandControl(), None, "rest"
        if action.name == "rest":
            return rest, HandControl(), action, "rest"
        u = (time - action.start) / action.duration
        end_stroke = action.preparation + action.stroke
        end_hold = end_stroke + action.hold
        if u < action.preparation:
            v = smooth(u / action.preparation) if action.preparation else 1
            amount, phase = -0.05 * v, "preparation"
        elif u < end_stroke:
            v = (u - action.preparation) / action.stroke
            warp = action.style.speed * v / (1 + (action.style.speed - 1) * v)
            anticipation = -0.05 if action.preparation else 0.0
            amount, phase = anticipation + (1 - anticipation) * smooth(warp), "stroke"
            amount += action.style.overshoot * math.sin(math.pi * v) ** 2
        elif u <= end_hold:
            amount, phase = 1.0, "hold"
        else:
            v = (u - end_hold) / (1 - end_hold)
            amount, phase = 1 - smooth(v), "recovery"
        target = action.target or Target(_GOALS[action.name])
        goal = target.position if target.space == "world" else self._relative(target.position, time)
        target_position = rest.lerp(goal, amount * action.style.amplitude)
        distance = self.arm.length
        if phase == "stroke":
            fraction = (u - action.preparation) / action.stroke
            target_position += Vec3(0, -action.style.arc * distance * math.sin(math.pi * fraction) ** 2, 0)
        if phase == "hold" and action.style.settling and action.hold:
            elapsed = time - action.stroke_at
            # The wobble fades to rest by the end of the hold so recovery starts from the held pose.
            fade = 1 - smooth(elapsed / (action.hold * action.duration))
            onset = smooth(elapsed / min(1 / 18, action.hold * action.duration / 2))
            wobble = math.sin(elapsed * 18) * math.exp(-elapsed * 9) * fade * onset
            target_position += Vec3(0, wobble * action.style.settling * distance * 0.03, 0)
        target_position += Vec3(action.style.asymmetry * distance * math.sin(math.pi * u) ** 2 * 0.05, 0, 0)
        control = action.control or _recipe(action.name, self.hand, time - action.start)
        control = replace(control, curl=control.curl + (1 - control.curl) * action.style.tension * 0.2)
        # Ease into and out of the clamp: anticipation and overshoot must not create finger velocity jumps.
        weight = smooth(amount)
        blended = _blend(HandControl(), control, weight, self.hand) if weight else HandControl()
        return target_position, blended, action, phase

    def _contact_request(self, contact: Contact, time: float, control: HandControl) -> tuple[Vec3, Quaternion]:
        frame = contact.frame(time)
        if contact.digit is None:
            return frame.origin, frame.rotation
        fingers = replace(control, wrist_flex=0, wrist_deviation=0, forearm_twist=0)
        offset = hand_pose(self.hand, fingers, Frame(), side=self.arm.side).digit(contact.digit).points[-1]
        return frame.origin - frame.rotation.rotate(offset), frame.rotation

    def _contact_position(self, action: Action, time: float, fallback: Vec3) -> Vec3:
        contacts = [c for c in self.contacts if action.start < c.start < c.end < action.end]
        active = next((c for c in contacts if c.start <= time <= c.end), None)
        if active:
            return self._contact_request(active, time, self._request(time)[1])[0]
        if not contacts:
            return fallback
        previous = next((c for c in reversed(contacts) if c.end < time), None)
        following = next((c for c in contacts if c.start > time), None)
        start = previous.end if previous else action.start
        end = following.start if following else action.end
        span = end - start
        u = (time - start) / span

        def position(contact: Contact | None, at: float) -> Vec3:
            if contact:
                return self._contact_request(contact, at, self._request(at)[1])[0]
            return self._relative(_GOALS['rest'], at)

        def velocity(contact: Contact | None, at: float) -> Vec3:
            h = min(1e-4, span * 1e-3)
            lo, hi = max(0.0, at - h), at + h
            return (position(contact, hi) - position(contact, lo)) / (hi - lo)

        ta = u - 6 * u**3 + 8 * u**4 - 3 * u**5
        tb = -4 * u**3 + 7 * u**4 - 3 * u**5
        return (
            position(previous, start).lerp(position(following, end), smooth(u))
            + (velocity(previous, start) * ta + velocity(following, end) * tb) * span
        )

    def _pole_geometry(self, action: Action, time: float, goal: Vec3) -> tuple[Vec3, Vec3, float]:
        root = self.root.sample(time)
        shoulder = root.point(self.arm.shoulder)
        default = root.point(self.arm.shoulder + Vec3(1 if self.arm.side == 'right' else -1, 0, 0))
        delta = goal - shoulder
        direction = delta.unit() if delta.length > 1e-12 else Vec3(0, 1, 0)

        def bend(pole: Vec3) -> Vec3:
            toward = pole - shoulder
            projected = toward - direction * toward.dot(direction)
            if projected.length < 1e-10:
                axis = Vec3(1, 0, 0) if abs(direction.x) < 0.9 else Vec3(0, 0, 1)
                projected = axis - direction * axis.dot(direction)
            return projected.unit()

        assert action.pole is not None
        a, b = bend(default), bend(action.pole)
        return direction, a, math.atan2(direction.dot(a.cross(b)), a.dot(b))

    @cached_property
    def _pole_paths(self) -> dict[tuple[int, float, float], tuple[tuple[float, ...], tuple[float, ...]]]:
        # At most two transitions are retained; derived data never enters motion serialization or equality.
        return {}

    def _pole_path(self, action: Action, start: float, end: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
        key = (id(action), start, end)
        if key in self._pole_paths:
            return self._pole_paths[key]
        knots = {start, end, action.stroke_at}
        knots.update(k.time for k in self.root.keys)
        for contact in self.contacts:
            if action.start < contact.start < contact.end < action.end:
                knots.update((contact.start, contact.end))
                knots.update(k.time for k in contact.target.keys)
        ordered = sorted(t for t in knots if start <= t <= end)
        if (len(ordered) - 1) * 32 + 1 > 100000:
            raise LimbError('pole winding exceeds its 100000-sample preparation budget', code='budget')
        times = [ordered[0]]
        for a, b in zip(ordered, ordered[1:], strict=False):
            for i in range(1, 33):
                t = b if i == 32 else a + (b - a) * i / 32
                if t > times[-1]:
                    times.append(t)
        angles: list[float] = []
        for t in times:
            goal = self._contact_position(action, t, self._request(t)[0])
            raw = self._pole_geometry(action, t, goal)[2]
            previous = angles[-1] if angles else raw
            angles.append(previous + math.atan2(math.sin(raw - previous), math.cos(raw - previous)))
        result = (tuple(times), tuple(angles))
        if len(self._pole_paths) >= 2:
            self._pole_paths.clear()
        self._pole_paths[key] = result
        return result

    def _pole(self, action: Action | None, time: float, goal: Vec3) -> Vec3:
        root = self.root.sample(time)
        shoulder = root.point(self.arm.shoulder)
        default = root.point(self.arm.shoulder + Vec3(1 if self.arm.side == 'right' else -1, 0, 0))
        if action is None or action.pole is None:
            return default
        u = (time - action.start) / action.duration
        arrival = action.preparation or action.stroke
        recovery = action.preparation + action.stroke + action.hold
        weight = smooth(u / arrival) * (1 - smooth((u - recovery) / (1 - recovery)))
        if weight == 0:
            return default
        if weight == 1:
            return action.pole
        start, end = (
            (action.start, action.start + arrival * action.duration)
            if u < arrival
            else (action.start + recovery * action.duration, action.end)
        )
        times, angles = self._pole_path(action, start, end)
        reference = angles[max(0, bisect_right(times, time) - 1)]
        direction, bend, angle = self._pole_geometry(action, time, goal)
        angle += 2 * math.pi * round((reference - angle) / (2 * math.pi))
        return shoulder + Quaternion.axis_angle(direction, angle * weight).rotate(bend)

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
        goal, control, action, phase = self._request(time)
        orientation: Quaternion | None = None
        local_orientation = False
        active: Contact | None = None
        if action is not None:
            contacts = [c for c in self.contacts if action.start < c.start < c.end < action.end]
            active = next((c for c in contacts if c.start <= time <= c.end), None)
            if active:
                goal, orientation = self._contact_request(active, time, control)
            elif contacts:
                previous = next((c for c in reversed(contacts) if c.end < time), None)
                following = next((c for c in contacts if c.start > time), None)
                start_time = previous.end if previous else action.start
                end_time = following.start if following else action.end

                def endpoint(contact: Contact | None, at: float) -> tuple[Vec3, Quaternion]:
                    if contact:
                        return self._contact_request(contact, at, self._request(at)[1])
                    rest = self._relative(_GOALS["rest"], at)
                    profile = replace(self.arm, shoulder=self.root.sample(at).point(self.arm.shoulder))
                    endpoint_pole = self._pole(action, at, rest)
                    resting = reach(profile, rest, pole=endpoint_pole, policy=self.reach_policy)
                    return rest, resting.frame.rotation

                a, qa = endpoint(previous, start_time)
                b, qb = endpoint(following, end_time)
                span = end_time - start_time
                u = (time - start_time) / span
                weight = smooth(u)

                # Quintic Hermite coefficients for matching endpoint angular velocity.
                ta = u - 6 * u**3 + 8 * u**4 - 3 * u**5
                tb = -4 * u**3 + 7 * u**4 - 3 * u**5
                if action.pole is not None:
                    # Blend wrist offsets in the moving arm frame, so the pole's turn does not become wrist twist.
                    def relative_rotation(at: float, target: Vec3, rotation: Quaternion) -> Quaternion:
                        profile = replace(self.arm, shoulder=self.root.sample(at).point(self.arm.shoulder))
                        arm = reach(profile, target, pole=self._pole(action, at, target), policy=self.reach_policy)
                        return arm.frame.rotation.inverse() * rotation

                    qa = relative_rotation(start_time, a, qa)
                    qb = relative_rotation(end_time, b, qb)
                    local_orientation = True
                goal, orientation = self._contact_position(action, time, goal), qa.slerp(qb, weight)

                def angular_velocity(contact: Contact | None, at: float) -> Vec3:
                    h = min(1e-4, span * 1e-3)
                    lo, hi = max(0.0, at - h), at + h
                    p, q0 = endpoint(contact, lo)
                    q, q1 = endpoint(contact, hi)
                    if action.pole is not None:
                        q0, q1 = relative_rotation(lo, p, q0), relative_rotation(hi, q, q1)
                    delta = q0.inverse() * q1
                    if delta.w < 0:
                        delta = -delta
                    vector = Vec3(delta.x, delta.y, delta.z)
                    if vector.length < 1e-12:
                        return Vec3()
                    return vector.unit() * (2 * math.atan2(vector.length, delta.w) / (hi - lo))

                turn = (angular_velocity(previous, start_time) * ta + angular_velocity(following, end_time) * tb) * span
                if turn.length > 1e-12:
                    orientation = orientation * Quaternion.axis_angle(turn, turn.length)
        root = self.root.sample(time)
        profile = replace(self.arm, shoulder=root.point(self.arm.shoulder))
        pole = self._pole(action, time, goal)
        arm = reach(profile, goal, pole=pole, policy=self.reach_policy)
        if orientation is not None:
            relative = orientation if local_orientation else arm.frame.rotation.inverse() * orientation
            x, y, z = (relative.rotate(v) for v in (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)))
            control = replace(
                control,
                wrist_flex=math.asin(max(-1, min(1, -z.y))),
                wrist_deviation=math.atan2(x.y, y.y),
                forearm_twist=math.atan2(z.x, z.z),
            )
        for name, limit in (
            ("wrist_flex", profile.flex_limit),
            ("wrist_deviation", profile.deviation_limit),
            ("forearm_twist", profile.twist_limit),
        ):
            bounded(getattr(control, name), *limit, name)
        hand = hand_pose(self.hand, control, arm.frame, side=profile.side)
        diagnostics: tuple[Diagnostic, ...] = ()
        if active:
            at = hand.frame.origin if active.digit is None else hand.digit(active.digit).points[-1]
            error = at.distance(active.frame(time).origin)
            if error > 1e-6:
                raise LimbError(f"contact {active.name} has residual {error:g}", code="contact", residual=error)
            diagnostics = (Diagnostic("contact", active.name, error),)
        return Sample(time, arm, hand, control, action.name if action else "rest", phase, diagnostics)

    def prop_frame(self, name: str, time: float) -> Frame:
        number(time, "prop time")
        for attachment in self.attachments:
            if attachment.name == name:
                if time < attachment.attach:
                    return attachment.initial
                return self.sample(min(time, attachment.release)).hand.frame.compose(attachment.offset)
        raise LimbError(f"unknown attached prop {name!r}")


def sample_motion(motion: Motion, time: float, *, track: str) -> Sample:
    """Sample a named compilation input while retaining the originating motion's error context."""
    try:
        return motion.sample(time)
    except LimbError as error:
        raise error.with_context(track=track) from error
