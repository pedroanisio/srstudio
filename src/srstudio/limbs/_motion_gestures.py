"""Anatomy-aware gesture requests and hand-control blending, before contact constraints."""

from __future__ import annotations

import math
from dataclasses import fields, replace
from typing import TYPE_CHECKING

from ._motion_interpolation import smooth
from .errors import LimbError
from .math3d import Vec3
from .model import HandControl, HandProfile

if TYPE_CHECKING:
    from .motion import Action, Motion

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


def relative(motion: Motion, point: Vec3, time: float) -> Vec3:
    root = motion.root.sample(time)
    v = point.mirror() if motion.arm.side == "left" else point
    return root.point(motion.arm.shoulder) + root.rotation.rotate(v * motion.arm.length)


def request(motion: Motion, time: float) -> tuple[Vec3, HandControl, Action | None, str]:
    rest = motion._relative(_GOALS["rest"], time)
    action = next((a for a in motion.actions if a.start <= time < a.end), None)
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
    target = action.target
    if not target:
        goal = motion._relative(_GOALS[action.name], time)
    else:
        goal = target.position if target.space == "world" else motion._relative(target.position, time)
    target_position = rest.lerp(goal, amount * action.style.amplitude)
    distance = motion.arm.length
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
    control = action.control or _recipe(action.name, motion.hand, time - action.start)
    control = replace(control, curl=control.curl + (1 - control.curl) * action.style.tension * 0.2)
    # Ease into and out of the clamp: anticipation and overshoot must not create finger velocity jumps.
    weight = smooth(amount)
    blended = _blend(HandControl(), control, weight, motion.hand) if weight else HandControl()
    return target_position, blended, action, phase
