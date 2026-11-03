"""The first-delivery gate on held changes the engine shows a frame late (ADR 0216).

scene-render draws frame ``k`` at ``t = k / fps`` and shows a held change from its time on: a hold or step key, a
node's ``start``, its ``end``. A change keyed for frame ``k`` that the engine reaches a hair after ``k / fps`` shows on
frame ``k + 1``, and frame ``k`` repeats the frame before. :func:`late_changes` finds every such change from the scene
alone, doing the engine's arithmetic in the engine's order: a sequence's placement of its shots end to end, each
group's ``timeOffset`` and ``timeScale`` clock, and the time base of each key. :func:`late_defects` refuses a reel on
its first delivery that holds one; ``Canvas(held_frames=True)`` keys held changes half a frame early, so a new reel
built with it holds none.

A change is meant for frame ``k`` when it is written on the frame grid, within :data:`~srstudio.held_keys.SLACK` of a
frame of its own timeline, and lands there in the reel: within the same slack of frame ``k``'s sample time. A change
keyed for a shot's own frame lands between the reel's frames when the shot starts between them, and is shown on the
next frame as written; one half a frame off the grid, as a new canvas keys it, is meant for no frame time. Neither is
late. A timing the gate cannot follow (a normalized time base, a marker, a stopped or reversed clock, a media clock
over drawn nodes) is refused rather than passed.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from . import held_keys
from .frame_gates import FrameGateError
from .held_keys import MAX_FPS, SLACK
from .releases import Release
from .social import Drift

__all__ = ["Late", "late_changes", "late_defects", "refusal"]

HELD = frozenset({"hold", "step"})  # interpolations that keep a key's value until the next key
_NOT_NODES = frozenset({"animate", "key", "textAnimator", "transition"})  # elements, not nodes: no window, no clock
_SHOWN = 6  # late changes a refusal lists by name; the frames it names are all of them


@dataclass(frozen=True)
class Late:
    """A held change the engine shows a frame late: ``frame`` repeats the frame before it, since the engine reaches
    the change ``by`` seconds of its own timeline after the frame's sample time."""

    frame: int
    node: str
    what: str
    by: float

    def __str__(self) -> str:
        return f"{self.node} {self.what} on frame {self.frame}"


@dataclass(eq=False)
class _Node:
    el: ET.Element
    parent: _Node | None
    start: float
    end: float | None
    clock: list[float] | None = None  # [origin, offset, scale], as the engine keeps it
    placed: bool = False  # a sequence's shot, put where the shot before it ends
    crossed: bool = False  # a shot a transition crosses into or out of: its window is widened, not cut
    children: list[_Node] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.el.get("id") or f"<{self.el.tag}>"


@dataclass(frozen=True)
class _Change:
    node: _Node
    value: float  # where the change is on the node's channel: its timeline, or its local time
    written: float  # the time as the scene writes it, on its own grid
    local: bool
    what: str


def _cannot(why: str) -> FrameGateError:
    return FrameGateError(f"the held-key gate cannot follow {why}")


def _seconds(el: ET.Element, name: str) -> float | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        raise _cannot(f"{el.get('id') or el.tag}'s {name}={raw!r}: not a number of seconds") from None
    if not math.isfinite(value):
        raise _cannot(f"{el.get('id') or el.tag}'s {name}={raw!r}: not a finite time")
    return value


def _rate(project: ET.Element) -> Fraction:
    try:
        rate = Fraction(project.get("fps", ""))
    except (ValueError, ZeroDivisionError):
        raise FrameGateError(f"a scene with fps={project.get('fps')!r} has no frame grid to judge") from None
    if not 0 < rate <= MAX_FPS:
        raise FrameGateError(f"a scene with fps={project.get('fps')!r} has no frame grid to judge")
    return rate


def _build(el: ET.Element, parent: _Node | None) -> _Node:
    if el.get("startMarker") is not None or el.get("endMarker") is not None:
        raise _cannot(f"{el.get('id') or el.tag}'s marker: place it by its time")
    node = _Node(el, parent, _seconds(el, "start") or 0.0, _seconds(el, "end"))
    offset, scale = _seconds(el, "timeOffset") or 0.0, _seconds(el, "timeScale")
    scale = 1.0 if scale is None else scale
    if el.tag in ("group", "sequence") and (offset != 0.0 or scale != 1.0):
        if scale <= 0.0:
            raise _cannot(f"{node.id}'s timeScale={scale!r}: a clock that stops or runs back")
        node.clock = [node.start, offset, scale]
    drawn = [c for c in el if c.tag not in _NOT_NODES]
    if el.tag == "layer" and drawn:
        raise _cannot(f"{node.id}'s media clock over drawn nodes")
    node.children = [_build(c, node) for c in drawn]
    if el.tag == "sequence":
        _place(node)
    return node


def _place(seq: _Node) -> None:
    """The engine's ``place_sequence``: each shot starts where the one before it ends, plus the gap."""
    gap = _seconds(seq.el, "timeGap") or 0.0
    crossed = seq.el.get("transition") is not None or any(c.tag == "transition" for c in seq.el)
    cursor = seq.start
    for shot in seq.children:
        own = shot.start
        length = None if shot.end is None else shot.end - shot.start
        _shift(shot, (cursor + own) - own)
        shot.placed, shot.crossed = True, crossed
        cursor = math.inf if length is None else shot.start + length + gap


def _shift(node: _Node, delta: float) -> None:
    if delta == 0.0:
        return
    for n in _walk(node):
        n.start += delta
        if n.end is not None:
            n.end += delta
        if n.clock is not None:
            n.clock[0] += delta


def _walk(node: _Node) -> Iterator[_Node]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _ancestors(node: _Node) -> list[_Node]:
    """From the root down to ``node``'s parent: the clocks that map composition time to ``node``'s timeline."""
    chain: list[_Node] = []
    while node.parent is not None:
        node = node.parent
        chain.append(node)
    return chain[::-1]


def _changes(node: _Node) -> Iterator[_Change]:
    for edge, value in (("start", node.start), ("end", node.end)):
        written = _seconds(node.el, edge)
        if value is None or node.crossed or (written is None and not (node.placed and edge == "start")):
            continue
        # a shot's own start is relative to where the sequence puts it: written as 0 when it opens there
        yield _Change(node, value, written or 0.0, False, f"{edge} {value:.9g}")
    for animate in (c for c in node.el if c.tag == "animate"):
        base = animate.get("timeBase", "composition")
        if base not in ("composition", "local"):
            raise _cannot(f"{node.id}'s {base!r} time base")
        default = animate.get("defaultInterpolation", "linear")
        keys = sorted(((_seconds(k, "time"), k) for k in animate if k.tag == "key"), key=lambda tk: tk[0] or 0.0)
        for (_, before), (time, key) in zip(keys, keys[1:], strict=False):
            if time is None or before.get("interpolation", default) not in HELD:
                continue
            if before.get("value") == key.get("value"):
                continue
            prop = animate.get("property", "value")
            yield _Change(node, time, time, base == "local", f"{prop} key {key.get('time')}")


def _clocked(chain: list[_Node], t: float) -> float:
    """Composition time ``t`` on the timeline under ``chain``, with the engine's float operations."""
    for n in chain:
        if n.clock is not None:
            origin, offset, scale = n.clock
            t = origin + (t - origin - offset) * scale
    return t


def _unclocked(chain: list[_Node], t: Fraction) -> Fraction:
    """The composition time, exactly, at which ``chain``'s clocks read ``t``."""
    for n in reversed(chain):
        if n.clock is not None:
            origin, offset, scale = (Fraction(x) for x in n.clock)
            t = origin + offset + (t - origin) / scale
    return t


def _on_grid(time: Fraction, rate: Fraction) -> int | None:
    """The frame ``time`` is written for, within :data:`SLACK` of it, or None."""
    frames = time * rate
    nearest = round(frames)
    return nearest if abs(frames - nearest) <= Fraction(SLACK) else None


def late_changes(document: bytes) -> list[Late]:
    """Every held change in the scene ``document`` that the engine shows a frame after the frame it is meant for,
    in frame order. A scene that is not one, or whose timing the gate cannot follow, is a :class:`FrameGateError`."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError as e:
        raise FrameGateError(f"not a scene document: {e}") from None
    project, composition = root.find("project"), root.find("composition")
    if project is None:
        raise FrameGateError("a scene with no project has no frame grid to judge")
    rate = _rate(project)
    duration = _seconds(project, "duration") or 0.0
    count = held_keys.frame_count(duration, rate)
    late: list[Late] = []
    if composition is None:
        return late
    for top in (_build(c, None) for c in composition if c.tag not in _NOT_NODES):
        for node in _walk(top):
            chain = _ancestors(node)
            for change in _changes(node):
                if _on_grid(Fraction(change.written), rate) is None:
                    continue  # meant for no frame of its own timeline
                at = Fraction(change.value) + (Fraction(node.start) if change.local else 0)
                frame = _on_grid(_unclocked(chain, at), rate)
                if frame is None or not 0 <= frame < count:
                    continue  # lands between the reel's frames, or outside them
                shown = _clocked(chain, (frame * rate.denominator) / rate.numerator)
                if change.local:
                    shown = shown - node.start
                if shown < change.value:
                    late.append(Late(frame, node.id, change.what, change.value - shown))
    return sorted(late, key=lambda x: (x.frame, x.node, x.what))


def refusal(late: Sequence[Late]) -> str:
    """What a delivery gate says of a reel with these ``late`` changes: every frame, and the first few by name."""
    frames = ", ".join(str(f) for f in sorted({x.frame for x in late}))
    named = "; ".join(map(str, late[:_SHOWN])) + ("; ..." if len(late) > _SHOWN else "")
    return (
        f"held keys: {len(late)} held changes show a frame late, on frames {frames} ({named}): "
        "rebuild with held_frames=True (ADR 0216)"
    )


def late_defects(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> list[Drift]:
    """Each reel on its ``first`` delivery (slug to video name) whose scene holds a held change the engine shows a
    frame late. A project with no scene has nothing to judge; a scene the gate cannot read is refused."""
    drift: list[Drift] = []
    for slug, video in first.items():
        scene = Path(episodes) / slug / releases[slug].scene_file
        if not scene.is_file():
            continue
        try:
            late = late_changes(scene.read_bytes())
        except FrameGateError as e:
            drift.append(Drift(video, f"held keys: {e}"))
            continue
        if late:
            drift.append(Drift(video, refusal(late)))
    return drift
