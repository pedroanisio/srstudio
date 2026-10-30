"""A Toon head that moves on its own (ADR 0050): the figure drawn in nested groups instead of flat layers, the head
rotating about the neck behind a body whose ruff covers the seam, played from a :class:`srstudio.head_motion.HeadPlan`.

The nesting is outermost first, each group carrying one kind of motion, so no property has two sources:

* ``lean`` turns everything about the seat, ``breath`` swells it from the seat;
* the head chain goes behind the body: ``turn`` (the drawn tilt plus glances and the trail behind the body) about the
  neck, ``nod`` (a roll about the neck and a drop), ``idle`` (the wander), ``lift`` (the breath's rise);
* inside it the skull, then ``face``, which slides over the skull: further than the skull on a nod and sideways on a
  glance, the way a turned head foreshortens;
* the body with its arms comes after the head chain, its ruff over the seam, then anything held in front of the face.

A :class:`HeadRig` supplies the three drawings. Nothing here changes :func:`srstudio.toon_cast.figure`: a character
moves its head only when a script draws it through :func:`figure`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol, cast, runtime_checkable

from .canvas import Canvas
from .head_motion import GAZES, Channel, HeadMotionError, HeadPlan, HeadStyle
from .toon import Pose, ToonDataError, fh, fx, fy, runs, swap_frames
from .toon_cast import (
    PIVOT,
    SHUT,
    Layer,
    Look,
    Mouths,
    Point,
    _arms,
    _draw,
    _draw_blinks,
    _draw_mouth,
    _eye,
    _mouth,
    _place,
    _teeth,
    _whiskers,
)

__all__ = ["FACE_SLIDE", "HeadRig", "figure", "gaze_states"]

FACE_SLIDE = 0.8  # how much further than the skull the face drops on a nod
_PUPIL_FREE = frozenset({"hearts", "wince", *SHUT})  # eyes with no pupil to move


@runtime_checkable
class _Pupils(Protocol):
    """A drawing that draws its own pupils, so a glance can move them."""

    pupil: Callable[..., list[Layer]]


@dataclass(frozen=True)
class HeadRig:
    """A character split at the neck. ``look`` is its look with an untilted head and a drawing whose pupils can move;
    ``skull`` draws the head closed under the chin, ``face`` what slides over it, ``trunk`` the body with a top that
    hides the seam. ``neck`` is where the head turns, ``tilt`` how it sits at rest (degrees clockwise), ``style`` how
    it moves."""

    look: Look
    neck: Point
    tilt: float
    skull: Callable[[], Sequence[Layer]]
    face: Callable[[], Sequence[Layer]]
    trunk: Callable[[], Sequence[Layer]]
    style: HeadStyle


def gaze_states(gaze: Sequence[tuple[float, str]], start: float, end: float) -> dict[str, list[tuple[float, int]]]:
    """Opacity hold keys per gaze of a run from ``start`` to ``end``: the one looking that way shows, ``ahead``
    first."""
    current = "ahead"
    timeline: list[tuple[float, str]] = []
    for t, name in gaze:
        if name not in GAZES:
            raise HeadMotionError(f"no gaze {name!r}")
        if t <= start:
            current = name
        elif t < end:
            timeline.append((t, name))
    names = dict.fromkeys(["ahead", current, *(name for _, name in timeline)])
    return {
        name: [(start, int(current == name)), *((t, int(state == name)) for t, state in timeline)] for name in names
    }


def _gazing(look: Look, name: str) -> Look:
    """``look`` with its pupils moved the way ``name`` looks."""
    drawing = look.drawing
    if not isinstance(drawing, _Pupils):
        raise ToonDataError(f"{look.name}: only a drawing with pupils of its own can glance")
    dx, dy = GAZES[name]
    r = look.eye_r
    base = drawing.pupil

    def pupil(face: Look, x: float, y: float, size: float) -> list[Layer]:
        return base(face, x + dx * r, y + dy * r, size)

    return replace(look, drawing=replace(cast(Any, drawing), pupil=pupil))


def _animate(cv: Canvas, node, prop: str, channel: Channel, scale: float = 1.0, base: float = 0.0) -> None:
    """``channel`` as engine keys on ``prop``; spring keys carry their momentum into the next key."""
    if not channel.keys:
        return
    curve = "spring" if channel.spring else channel.curve
    a = node.add_animate(property=prop, defaultInterpolation=curve)
    attrs = channel.spring.attributes() if channel.spring else {}
    for i, (t, value) in enumerate(channel.keys):
        carry = {"carry": "true"} if channel.spring and i else {}
        a.add_key(time=round(t, 6), value=str(round(base + value * scale, 4)), **attrs, **carry)


def _eyes(cv: Canvas, parent, look: Look, kind: str, arms: str, gaze, start: float, end: float) -> None:
    def draw(into, seen: Look) -> None:
        left = _eye(seen, seen.eyes[0], kind, 1.0)
        right = _eye(seen, seen.eyes[1], kind, -1.0)
        _draw(cv, into, _place(left + right, arms))

    states = gaze_states(gaze, start, end)
    if kind in _PUPIL_FREE or set(states) == {"ahead"}:
        draw(parent, look)
        return
    for name, keys in states.items():
        layer = cv.group(parent, cv.uid("g"))
        draw(layer, _gazing(look, name))
        cv.keys(layer, "opacity", keys, local=False)


def figure(
    cv: Canvas,
    parent,
    rig: HeadRig,
    poses: Sequence[Pose],
    duration: float,
    plan: HeadPlan,
    taps: Sequence[float] = (),
    enter: float = 0.0,
    stickers: Sequence[Layer] = (),
    mouths: Mouths = (),
):
    """The character in nested groups (the module's docstring), one drawing per pose run inside the chains, moved by
    ``plan``. The arguments mean what they mean to :func:`srstudio.toon_cast.figure`. Returns the outermost group."""
    from .toon_wear import face_of, wear_layers  # here, not at import: toon_wear draws with toon_cast

    look = rig.look
    style = rig.style
    seat_x, seat_y = fx(PIVOT[0]), fy(PIVOT[1])
    neck_x, neck_y = fx(rig.neck[0]), fy(rig.neck[1])
    seat = {"x": seat_x, "y": seat_y, "anchorX": seat_x, "anchorY": seat_y}
    neck = {"x": neck_x, "y": neck_y, "anchorX": neck_x, "anchorY": neck_y}

    lean = cv.group(parent, cv.uid("lean"), **seat)
    _animate(cv, lean, "rotation", plan.lean)
    breath = cv.group(lean, cv.uid("breath"), **seat)
    _animate(cv, breath, "scaleY", plan.breath, style.breath_scale, 1.0)
    turn = cv.group(breath, cv.uid("turn"), rotation=rig.tilt, **neck)
    _animate(cv, turn, "rotation", plan.turn, base=rig.tilt)
    nod = cv.group(turn, cv.uid("nod"), **neck)
    _animate(cv, nod, "rotation", plan.roll)
    _animate(cv, nod, "y", plan.nod, fh(1.0), neck_y)
    idle = cv.group(nod, cv.uid("idle"), **neck)
    _animate(cv, idle, "rotation", plan.idle_roll)
    _animate(cv, idle, "y", plan.idle_y, fh(1.0), neck_y)
    lift = cv.group(idle, cv.uid("lift"))
    _animate(cv, lift, "y", plan.breath, -fh(style.breath_px))
    skull = cv.group(lift, cv.uid("skull"))
    face = cv.group(lift, cv.uid("face"))
    _animate(cv, face, "x", plan.face_x, fh(1.0))
    _animate(cv, face, "y", plan.nod, fh(FACE_SLIDE))
    trunk = cv.group(breath, cv.uid("trunk"))
    front = cv.group(breath, cv.uid("front"))

    for pose, start, end in runs(poses, duration - enter):
        start, end = round(start + enter, 6), round(end + enter, 6)
        arms = pose.arms
        _draw(cv, cv.group(skull, cv.uid("g"), start=start, end=end), _place(list(rig.skull()), arms))

        g = cv.group(face, cv.uid("g"), start=start, end=end)
        _draw(cv, g, _place(list(rig.face()), arms))
        _eyes(cv, g, look, pose.eyes, arms, plan.gaze, start, end)
        cheeks, worn = wear_layers(face_of(look), pose.wear) if pose.wear else ([], [])
        _draw(cv, g, _place(cheeks + (_whiskers(look) if look.whiskers else []), arms))
        _draw_mouth(cv, g, look, pose, _place(_mouth(look, pose.mouth), arms), mouths, start, end)
        _draw_blinks(cv, g, look, pose, start, end)
        bare = look.teeth and pose.mouth not in ("none", "grimace", "kiss", "scream")
        _draw(cv, g, _place((_teeth(look) if bare else []) + worn + list(stickers), arms))

        body = cv.group(trunk, cv.uid("g"), start=start, end=end)
        _draw(cv, body, _place(list(rig.trunk()), arms))
        if arms == "type":

            def frame_of(into, frame: int) -> None:
                _draw(cv, into, _place(_arms(look, "type", frame)[0], "type"))

            swap_frames(cv, body, start, end, taps, frame_of)
            over: list[Layer] = []
        else:
            under, over = _arms(look, arms, 0)
            _draw(cv, body, _place(under, arms))
        if over:
            _draw(cv, cv.group(front, cv.uid("g"), start=start, end=end), _place(over, arms))
    return lean
