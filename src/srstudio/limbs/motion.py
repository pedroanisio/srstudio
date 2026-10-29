"""History-independent gestures, word timing, moving contacts and explicit prop attachment lifetimes."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, fields, replace

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

    def __post_init__(self) -> None:
        if number(self.time, "transform key time") < 0:
            raise LimbError("transform key time must be non-negative")


@dataclass(frozen=True)
class TransformTrack:
    keys: tuple[TransformKey, ...]

    def __post_init__(self) -> None:
        if not self.keys or len(self.keys) > 10000:
            raise LimbError("a transform track needs one to 10000 keys")
        if any(a.time >= b.time for a, b in zip(self.keys, self.keys[1:], strict=False)):
            raise LimbError("transform key times must be strictly increasing")

    @classmethod
    def constant(cls, frame: Frame) -> TransformTrack:
        return cls((TransformKey(0, frame),))

    def sample(self, time: float) -> Frame:
        number(time, "sample time")
        if time <= self.keys[0].time:
            return self.keys[0].frame
        for a, b in zip(self.keys, self.keys[1:], strict=False):
            if time <= b.time:
                u = smooth((time - a.time) / (b.time - a.time))
                return Frame(a.frame.origin.lerp(b.frame.origin, u), a.frame.rotation.slerp(b.frame.rotation, u))
        return self.keys[-1].frame


@dataclass(frozen=True)
class Target:
    position: Vec3
    space: str = "relative"

    def __post_init__(self) -> None:
        if self.space not in ("relative", "world"):
            raise LimbError("target space must be relative or world")


@dataclass(frozen=True)
class MotionStyle:
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
    take: str
    index: int

    def __post_init__(self) -> None:
        label(self.take, "word take ID")
        if isinstance(self.index, bool) or not isinstance(self.index, int) or not 0 <= self.index < 1000000:
            raise LimbError("word reference needs an integer word index in 0..999999")


@dataclass(frozen=True)
class Action:
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
        matches = [take for take in takes if take.id == ref.take]
        if len(matches) != 1 or ref.index >= len(matches[0].words):
            raise LimbError(f"word reference {ref.take}:{ref.index} does not resolve uniquely")
        take = matches[0]
        word = take.words[ref.index]
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

    def _relative(self, point: Vec3, time: float) -> Vec3:
        root = self.root.sample(time)
        v = point.mirror() if self.arm.side == "left" else point
        return root.point(self.arm.shoulder) + root.rotation.rotate(v * self.arm.length)

    def _request(self, time: float) -> tuple[Vec3, HandControl, Action | None, str]:
        rest = self._relative(_GOALS["rest"], time)
        action = next((a for a in self.actions if a.start <= time < a.end), None)
        if action is None:
            return rest, HandControl(), None, "rest"
        u = (time - action.start) / action.duration
        end_stroke = action.preparation + action.stroke
        end_hold = end_stroke + action.hold
        if u < action.preparation:
            v = smooth(u / action.preparation) if action.preparation else 1
            amount, phase = -0.05 * v, "preparation"
        elif u < end_stroke:
            v = (u - action.preparation) / action.stroke
            warp = action.style.speed * v / (1 + (action.style.speed - 1) * v)
            amount, phase = -0.05 + 1.05 * smooth(warp), "stroke"
            amount += action.style.overshoot * math.sin(math.pi * v) ** 2
        elif u <= end_hold:
            amount, phase = 1.0, "hold"
        else:
            v = (u - end_hold) / (1 - end_hold)
            amount, phase = 1 - smooth(v), "recovery"
        if action.name == "rest":
            amount = 0
        target = action.target or Target(_GOALS[action.name])
        goal = target.position if target.space == "world" else self._relative(target.position, time)
        target_position = rest.lerp(goal, amount * action.style.amplitude)
        distance = self.arm.length
        if phase == "stroke":
            fraction = (u - action.preparation) / action.stroke
            target_position += Vec3(0, -action.style.arc * distance * math.sin(math.pi * fraction) ** 2, 0)
        if phase == "hold" and action.style.settling:
            elapsed = time - action.stroke_at
            target_position += Vec3(
                0, math.sin(elapsed * 18) * math.exp(-elapsed * 9) * action.style.settling * distance * 0.03, 0
            )
        target_position += Vec3(action.style.asymmetry * distance * math.sin(math.pi * u) ** 2 * 0.05, 0, 0)
        control = action.control or _recipe(action.name, self.hand, time - action.start)
        control = replace(control, curl=control.curl + (1 - control.curl) * action.style.tension * 0.2)
        return target_position, _blend(HandControl(), control, min(1, max(0, amount)), self.hand), action, phase

    def _contact_request(self, contact: Contact, time: float, control: HandControl) -> tuple[Vec3, Quaternion]:
        frame = contact.frame(time)
        if contact.digit is None:
            return frame.origin, frame.rotation
        fingers = replace(control, wrist_flex=0, wrist_deviation=0, forearm_twist=0)
        offset = hand_pose(self.hand, fingers, Frame(), side=self.arm.side).digit(contact.digit).points[-1]
        return frame.origin - frame.rotation.rotate(offset), frame.rotation

    def sample(self, time: float) -> Sample:
        if number(time, "sample time") < 0:
            raise LimbError("motion sample time must be non-negative")
        goal, control, action, phase = self._request(time)
        orientation: Quaternion | None = None
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
                    endpoint_root = self.root.sample(at)
                    endpoint_pole = (
                        action.pole
                        if action.pole is not None
                        else endpoint_root.point(self.arm.shoulder + Vec3(1 if self.arm.side == "right" else -1, 0, 0))
                    )
                    resting = reach(profile, rest, pole=endpoint_pole, policy=self.reach_policy)
                    return rest, resting.frame.rotation

                a, qa = endpoint(previous, start_time)
                b, qb = endpoint(following, end_time)
                weight = smooth((time - start_time) / (end_time - start_time))
                goal, orientation = a.lerp(b, weight), qa.slerp(qb, weight)
        root = self.root.sample(time)
        profile = replace(self.arm, shoulder=root.point(self.arm.shoulder))
        pole = (
            action.pole
            if action and action.pole is not None
            else root.point(self.arm.shoulder + Vec3(1 if self.arm.side == "right" else -1, 0, 0))
        )
        arm = reach(profile, goal, pole=pole, policy=self.reach_policy)
        if orientation is not None:
            relative = arm.frame.rotation.inverse() * orientation
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
