"""A Toon head that moves on its own (ADR 0050): the figure drawn in nested groups instead of flat layers, the head
rotating about the neck with the seam hidden, played from a :class:`srstudio.head_motion.HeadPlan`.

The nesting is outermost first, each group carrying one kind of motion, so no property has two sources:

* ``lean`` turns everything about the seat, ``breath`` swells it from the seat;
* the head chain goes behind the body: ``turn`` (the drawn tilt plus glances and the trail behind the body) about the
  neck, ``nod`` (a roll about the neck and a drop), ``idle`` (the wander), ``lift`` (the breath's rise);
* inside it the skull, then ``face``, which slides over the skull: further than the skull on a nod and sideways on a
  glance, the way a turned head foreshortens;
* the body with its arms goes over the head chain, its top hiding the seam (a ruff), or under it, with the head's own
  chin hiding the seam (:attr:`HeadRig.head_over`); anything held in front of the face comes last.

A :class:`HeadRig` holds what any drawing supplies: the head contour, the neck pivot, what covers the seam, the three
drawings and a :class:`srstudio.head_motion.HeadStyle`. :func:`open_seam` measures a rig at the bounds of its style; a
drawing that can glance has ``looking`` (:class:`Glancing`). Nothing here changes :func:`srstudio.toon_cast.figure`: a
character moves its head only when a script draws it through :func:`figure`, which a sketch does when its staging
names the character in ``heads`` (:mod:`srstudio.toon_rigs`).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol, runtime_checkable

from . import anatomy_ledger, brush, drawing_events
from .canvas import Canvas, _at_zero
from .head_motion import (
    CHANNELS,
    GAZES,
    SPRING_RUN,
    Channel,
    HeadMotionError,
    HeadPlan,
    HeadStyle,
    Key,
    _bake_spring,
    limit,
)
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
from .toon_torso import depth_in

__all__ = [
    "FACE_SLIDE",
    "SPRING_RUN",
    "TILT_EASE",
    "Glancing",
    "HeadRig",
    "figure",
    "gaze_states",
    "open_seam",
    "rest_springs",
]

TILT_EASE = 0.4  # seconds a held tilt takes to reach its pose's value, less when the pose is short, see _held_tilts

FACE_SLIDE = 0.8  # how much further than the skull the face drops on a nod
SEAM_ROOM = 2.0  # how far above a seam cover's line a head must still be behind it, reference pixels
_PUPIL_FREE = frozenset({"hearts", "wince", *SHUT})  # eyes with no pupil to move


@runtime_checkable
class Glancing(Protocol):
    """A drawing that can look away: ``looking`` is the same drawing with its pupils ``dx`` and ``dy`` eye radii off."""

    def looking(self, dx: float, dy: float) -> Glancing: ...


class Seam(Protocol):
    """What the seam checks read of a rig, whatever draws it."""

    @property
    def neck(self) -> Point: ...
    @property
    def tilt(self) -> float: ...
    @property
    def head(self) -> tuple[Point, ...]: ...
    @property
    def cover(self) -> tuple[Point, ...]: ...
    @property
    def style(self) -> HeadStyle: ...
    @property
    def head_over(self) -> bool: ...
    @property
    def free(self) -> float: ...
    @property
    def tilt_reach(self) -> tuple[float, float]: ...


@dataclass(frozen=True)
class HeadRig:
    """A character split at the neck, from what its drawing supplies. ``look`` is its look with an untilted head and a
    :class:`Glancing` drawing. ``head`` is the head's closed contour and ``neck`` where it turns, ``tilt`` how it sits
    at rest (degrees clockwise), ``style`` how it moves. ``skull`` draws the head, ``face`` what slides over it,
    ``trunk`` the body. ``cover`` is the top of that body, the line that hides the seam: drawn over the head as a ruff,
    or, with ``head_over``, hidden itself behind the head, whose chin lies over the body. ``free`` is how far from each
    end of ``cover`` the seam need not stay shut (the corners where a head may part from the shoulders). ``pose_tilt``
    is how far a kind of eyes tilts the head beyond ``tilt``, held from that pose to the next and eased in on the
    style's ``settle``, for a drawing whose expressions carry a tilt; ``tilt_reach`` is the least and the most it
    gives, which count toward the rig's bounds. ``face_slide`` is how much further than the skull the face drops on a
    nod, for a face that has less room on its head than most. ``drawn_as`` is the part and version the rig draws, for a
    rig whose version the anatomy rules read."""

    look: Look
    neck: Point
    tilt: float
    head: tuple[Point, ...]
    cover: tuple[Point, ...]
    skull: Callable[[], Sequence[Layer]]
    face: Callable[[], Sequence[Layer]]
    trunk: Callable[[], Sequence[Layer]]
    style: HeadStyle
    head_over: bool = False
    free: float = 0.0
    pose_tilt: Callable[[str], float] | None = None
    tilt_reach: tuple[float, float] = (0.0, 0.0)
    face_slide: float = FACE_SLIDE
    drawn_as: tuple[str, int] | None = None


def _bounds(rig: Seam) -> list[tuple[float, float]]:
    """The turns (degrees, the rest tilt included) and drops (reference pixels) at the corners of what ``rig``'s style
    can reach."""
    style = rig.style
    swing = limit(style, "turn") + limit(style, "roll") + limit(style, "idle_roll")
    down = limit(style, "nod") + limit(style, "idle_y")
    up = -(style.breath_px + limit(style, "idle_y"))
    low, high = rig.tilt_reach
    return [
        (rig.tilt + (high if sign > 0 else low) + sign * swing, drop) for sign in (-1.0, 1.0) for drop in (up, down)
    ]


def reach(rig: Seam) -> HeadPlan:
    """The head at rest, then at every corner of what ``rig``'s style can reach, a second each: what a rig's specimen
    shows of it (:func:`srstudio.specimens.rig_digest`)."""
    corners = _bounds(rig)
    turns = ((0.0, 0.0), *((k + 1.0, turn - rig.tilt) for k, (turn, _) in enumerate(corners)))
    drops = ((0.0, 0.0), *((k + 1.0, drop) for k, (_, drop) in enumerate(corners)))
    return HeadPlan(turn=Channel(turns), nod=Channel(drops))


def chest(rig: HeadRig) -> Point:
    """The top of the chest in the figure's own reference pixels: on the neck's line, under the lowest the head
    reaches at any corner of what its style can do. Something worn from here clears the face whatever the head does,
    at any scale, as long as it is drawn in the figure's coordinates (:func:`srstudio.toon_sketch.figure_group`)."""
    lowest = 0.0
    for turn, drop in _bounds(rig):
        a = math.radians(turn)
        for x, y in rig.head:
            dx, dy = x - rig.neck[0], y - rig.neck[1]
            lowest = max(lowest, rig.neck[1] + dx * math.sin(a) + dy * math.cos(a) + drop)
    return (rig.neck[0], lowest)


def open_seam(rig: Seam) -> list[tuple[Point, float, float]]:
    """Where the seam opens: every ``(point, turn, drop)`` on the cover line (:data:`SEAM_ROOM` above it for a ruff),
    more than :attr:`HeadRig.free` from its ends, that the head does not reach behind with every channel at its limit.
    Empty is a rig that holds."""
    room = 0.0 if rig.head_over else SEAM_ROOM
    line = [(x, y - room) for x, y in brush.spline(rig.cover, False, 4)]
    ends = (rig.cover[0], rig.cover[-1])
    kept = [p for p in line if min(math.dist(p, end) for end in ends) >= rig.free]
    out = []
    for turn, drop in _bounds(rig):
        a = math.radians(-turn)
        for p in kept:
            dx, dy = p[0] - rig.neck[0], p[1] - drop - rig.neck[1]
            back = (
                rig.neck[0] + dx * math.cos(a) - dy * math.sin(a),
                rig.neck[1] + dx * math.sin(a) + dy * math.cos(a),
            )
            if depth_in(rig.head, back)[0] < 0.0:
                out.append((p, turn, drop))
    return out


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
    if not isinstance(drawing, Glancing):
        raise ToonDataError(f"{look.name}: only a drawing that can move its own pupils can glance")
    dx, dy = GAZES[name]
    return replace(look, drawing=drawing.looking(dx, dy))


def _animate(
    cv: Canvas, node, prop: str, channel: Channel, scale: float = 1.0, base: float = 0.0, carried: bool = False
) -> None:
    """Emit engine keys, sampling long carried springs to bound renderer work; ``carried`` keeps them as they are."""
    if not channel.keys:
        return
    if cv._frozen:
        hold = channel.spring is None and channel.curve == "hold"
        cv.keys(node, prop, [(t, round(base + value * scale, 4)) for t, value in channel.keys], hold=hold, local=False)
        return
    if not carried:
        channel = _bake_spring(channel)
    curve = "spring" if channel.spring else channel.curve
    a = node.add_animate(property=prop, defaultInterpolation=curve)
    attrs = channel.spring.attributes() if channel.spring else {}
    for i, (t, value) in enumerate(channel.keys):
        carry = {"carry": "true"} if channel.spring and i else {}
        a.add_key(time=round(t, 6), value=str(round(base + value * scale, 4)), **attrs, **carry)


def _held_tilts(spans: Sequence[tuple[Pose, float, float]], tilt_of: Callable[[str], float]) -> tuple[Key, ...]:
    """Keys that hold each pose's tilt through that pose: the old value at its start, then its own :data:`TILT_EASE`
    later. A spring runs from one key towards the next, so a lone key at each start would lean into the pose after."""
    keys: list[Key] = []
    for pose, start, end in spans:
        value = tilt_of(pose.eyes)
        if not keys:
            keys.append((start, value))
        elif value != keys[-1][1]:
            keys += [(start, keys[-1][1]), (round(start + min(TILT_EASE, (end - start) / 2.0), 6), value)]
    return tuple(keys)


def rest_springs(setup, run: int = SPRING_RUN) -> None:
    """Apply a lossy compatibility optimization by resetting every ``run``-th carried spring key under ``setup``.

    Removing carried momentum changes the trajectory and may introduce visible velocity changes. Preview any
    result that uses this helper. New callers should use ``figure`` or ``Channel.during``: those paths automatically
    sample long spring chains while preserving carried motion, within their sampling precision and work budget.
    This helper remains available for existing scenes that intentionally use spring resets.
    """
    if run < 2:
        raise ToonDataError(f"a run of {run} carried keys carries nothing: use 2 or more")
    for animate in setup.iter("animate"):
        chain = [key for key in animate.iter("key") if key.carry]
        for key in chain[run - 1 :: run]:
            key.carry = None


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
    on_face: Callable[[Any], None] | None = None,
):
    """The character in nested groups (the module's docstring), one drawing per pose run inside the chains, moved by
    ``plan``. The arguments mean what they mean to :func:`srstudio.toon_cast.figure`; ``on_face`` draws into the face's
    group last, so what it adds moves with the head. Returns the outermost group."""
    plan.check_bounds(rig.style, frozen=bool(cv._frozen))
    return _draw_figure(cv, parent, rig, poses, duration, plan, taps, enter, stickers, mouths, on_face)


def _draw_reach(cv: Canvas, parent, rig: HeadRig, poses: Sequence[Pose], duration: float, taps=(), *, mouths=()):
    """Draw only the rig-derived aggregate envelope probe for immutable specimen fingerprints.

    ``reach`` folds roll/idle/pose tilt into turn and lift/idle into nod. Those combined geometry bounds are
    deliberately larger than one performance channel's allowance. No caller-supplied plan enters this path.
    """
    return _draw_figure(cv, parent, rig, poses, duration, reach(rig), taps, mouths=mouths)


def _draw_figure(
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
    on_face: Callable[[Any], None] | None = None,
):
    """Emit a preflighted performance or the fixed, rig-derived specimen probe."""
    if rig.drawn_as is not None:
        anatomy_ledger.note_part(cv, *rig.drawn_as)
    with drawing_events.drawing(rig):
        from .toon_wear import face_of, wear_layers  # here, not at import: toon_wear draws with toon_cast

        look = rig.look
        style = rig.style
        if not cv._frozen:
            plan = replace(plan, **{name: _bake_spring(getattr(plan, name)) for name in CHANNELS})  # type: ignore[arg-type]
        spans = [(p, round(s + enter, 6), round(e + enter, 6)) for p, s, e in runs(poses, duration - enter)]
        pose_tilt = Channel(_held_tilts(spans, rig.pose_tilt), style.settle) if rig.pose_tilt else None
        if cv._frozen:
            for name, channel in [(name, getattr(plan, name)) for name in CHANNELS] + [("pose_tilt", pose_tilt)]:
                if channel is not None and channel.keys:
                    _at_zero(channel.keys, channel.spring is None and channel.curve == "hold", name)
        seat_x, seat_y = fx(PIVOT[0]), fy(PIVOT[1])
        neck_x, neck_y = fx(rig.neck[0]), fy(rig.neck[1])
        seat = {"x": seat_x, "y": seat_y, "anchorX": seat_x, "anchorY": seat_y}
        neck = {"x": neck_x, "y": neck_y, "anchorX": neck_x, "anchorY": neck_y}

        lean = cv.group(parent, cv.uid("lean"), **seat)
        _animate(cv, lean, "rotation", plan.lean)
        breath = cv.group(lean, cv.uid("breath"), **seat)
        _animate(cv, breath, "scaleY", plan.breath, style.breath_scale, 1.0)
        trunk = cv.group(breath, cv.uid("trunk")) if rig.head_over else None
        turn = cv.group(breath, cv.uid("turn"), rotation=rig.tilt, **neck)
        _animate(cv, turn, "rotation", plan.turn, base=rig.tilt)
        held = turn
        if pose_tilt is not None:
            held = cv.group(turn, cv.uid("tilt"), **neck)
            _animate(cv, held, "rotation", pose_tilt, carried=True)  # approved rigs hold these keys, see check_rig
        nod = cv.group(held, cv.uid("nod"), **neck)
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
        _animate(cv, face, "y", plan.nod, fh(rig.face_slide))
        trunk = trunk if trunk is not None else cv.group(breath, cv.uid("trunk"))
        front = cv.group(breath, cv.uid("front"))

        for pose, start, end in spans:
            arms = pose.arms
            _draw(cv, cv.group(skull, cv.uid("g"), start=start, end=end), _place(list(rig.skull()), arms))

            g = cv.group(face, cv.uid("g"), start=start, end=end)
            _draw(cv, g, _place(list(rig.face()), arms))
            _eyes(cv, g, look, pose.eyes, arms, plan.gaze, start, end)
            cheeks, worn = wear_layers(face_of(look), pose.wear) if pose.wear else ([], [])
            nose = [(shape, "ink" if i == 0 else "white") for i, shape in enumerate(look.nose)]
            _draw(cv, g, _place(cheeks + nose + (_whiskers(look) if look.whiskers else []), arms))
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
        if on_face is not None:
            on_face(face)
        return lean
