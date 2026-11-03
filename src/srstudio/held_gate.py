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
late, though the second must land on the reel's half frames (below). A change written off its own grid whose time,
added to where its shot starts, is a frame's time to float rounding is meant for that frame: 0.02 + 0.28 is frame 9
at 30 fps, and the engine, reading frame 9 at local 0.27999999999999997, shows it on frame 10. A timing the gate
cannot follow (a normalized time base, a marker, a stopped or reversed clock, a media clock over drawn nodes) is
refused rather than passed.

A change written half a frame before a frame of its own clock, as a canvas built with ``held_frames=True`` keys it,
is meant for the reel's frame after it, and lands half a frame before one when its clock runs on the reel's frames. In
a shot that starts between the reel's frames it lands anywhere between them, and the frame that first shows it can be
the one its time meant or the one after or before: keyed on the shot's frames, not the reel's. That is refused too
(ADR 0223). :func:`clocks` gives :meth:`srstudio.canvas.Canvas.place_held` each node's clock, so a canvas keys every
held change half a frame before the reel's frame through the shot's start.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Protocol

from . import held_keys
from .frame_gates import FrameGateError
from .held_keys import MAX_FPS, SLACK
from .releases import Release
from .social import Drift

__all__ = ["Clock", "Late", "clocks", "late_changes", "late_defects", "refusal"]

HELD = frozenset({"hold", "step"})  # interpolations that keep a key's value until the next key
_NOT_NODES = frozenset({"animate", "key", "textAnimator", "transition"})  # elements, not nodes: no window, no clock
_SHOWN = 6  # late changes a refusal lists by name; the frames it names are all of them
_NOISE = Fraction(
    1, 10**6
)  # of a frame: float rounding, not timing. A sum of written times this close to a frame is it
_HALF = Fraction(1, 2)
SHOT_GRID = "shot grid"  # Late.why: a held key on its shot's frames, in a shot between the reel's frames (ADR 0223)


class _Element(Protocol):
    """What the gate reads of a scene element: an XML element, or a live scene node through :class:`_Live`."""

    @property
    def tag(self) -> Any: ...

    def get(self, key: str, default: None = None) -> str | None: ...

    def __iter__(self) -> Iterator[Any]: ...


class _Live:
    """An ``sr_core`` scene element read as the gate reads XML: its tag, its lexical attributes and its children."""

    __slots__ = ("raw", "_attrs")

    def __init__(self, raw: Any) -> None:
        self.raw = raw
        self._attrs: dict[str, str] = raw.attributes()

    @property
    def tag(self) -> str:
        return str(self.raw.xml_name)

    def get(self, key: str, default: None = None) -> str | None:
        return self._attrs.get(key, default)

    def __iter__(self) -> Iterator[_Live]:
        return (_Live(c) for c in self.raw.elements())


@dataclass(frozen=True)
class Late:
    """A held change the engine shows a frame late: ``frame`` repeats the frame before it, since the engine reaches
    the change ``by`` seconds of its own timeline after the frame's sample time."""

    frame: int
    node: str
    what: str
    by: float
    why: str = "late"  # or SHOT_GRID: keyed on its shot's frames, shown on ``frame`` (ADR 0223)

    def __str__(self) -> str:
        if self.why == SHOT_GRID:
            return f"{self.node} {self.what} on frame {self.frame}, keyed on its shot's frames"
        return f"{self.node} {self.what} on frame {self.frame}"


@dataclass(eq=False)
class _Node:
    el: _Element
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


def _seconds(el: _Element, name: str) -> float | None:
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


def _build(el: _Element, parent: _Node | None) -> _Node:
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


def _on_grid(time: Fraction, rate: Fraction, slack: Fraction = Fraction(SLACK)) -> int | None:
    """The frame ``time`` is written for, within ``slack`` of a frame of it, or None."""
    frames = time * rate
    nearest = round(frames)
    return nearest if abs(frames - nearest) <= slack else None


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
                at = _unclocked(chain, Fraction(change.value) + (Fraction(node.start) if change.local else 0))
                written = _on_grid(Fraction(change.written), rate) is not None
                # meant for a frame: written on its own timeline's frames, or summed to one by the shot it is in
                frame = _on_grid(at, rate) if written else _on_grid(at, rate, _NOISE)
                if frame is None:
                    off = _off_the_reels_half_frames(change, at, rate)
                    if off is not None and 0 <= math.ceil(at * rate) < count:
                        late.append(Late(math.ceil(at * rate), node.id, change.what, off, SHOT_GRID))
                    continue
                if not 0 <= frame < count:
                    continue  # outside the reel's frames
                shown = _clocked(chain, (frame * rate.denominator) / rate.numerator)
                if change.local:
                    shown = shown - node.start
                if shown < change.value:
                    late.append(Late(frame, node.id, change.what, change.value - shown))
    return sorted(late, key=lambda x: (x.frame, x.node, x.what))


def _off_the_reels_half_frames(change: _Change, at: Fraction, rate: Fraction) -> float | None:
    """How far, in seconds, a change written half a frame before a frame of its own clock lands from the reel's half
    frames, when it lands off them: None for any other change. A canvas with ``held_frames`` keys a change half a frame
    before the frame meant to show it; on a shot's clock that is the reel's frame only when the shot starts on one."""
    if _on_grid(Fraction(change.written) - _HALF / rate, rate, _NOISE) is None:
        return None
    nearest = _on_grid(at - _HALF / rate, rate)
    if nearest is not None:
        return None
    centre = (math.floor(at * rate) + _HALF) / rate
    return float(abs(at - centre))


def refusal(late: Sequence[Late]) -> str:
    """What a delivery gate says of a reel with these ``late`` changes: every frame, and the first few by name."""
    parts = []
    for why, says in (
        ("late", "show a frame late"),
        (SHOT_GRID, "are keyed on a shot's frames, not the reel's, and show a frame early or late"),
    ):
        these = [x for x in late if x.why == why]
        if not these:
            continue
        frames = ", ".join(str(f) for f in sorted({x.frame for x in these}))
        named = "; ".join(map(str, these[:_SHOWN])) + ("; ..." if len(these) > _SHOWN else "")
        parts.append(f"{len(these)} held changes {says}, on frames {frames} ({named})")
    return f"held keys: {'; '.join(parts)}: rebuild with held_frames=True (ADR 0216, ADR 0223)"


@dataclass(frozen=True)
class Clock:
    """A node's place on the reel: where its own timeline starts (``start``, for a local key) and the clocks of its
    ancestors from the root down, each ``(origin, offset, scale)`` as the engine keeps it."""

    start: float
    chain: tuple[tuple[float, float, float], ...] = ()

    def _start(self, rate: Fraction) -> tuple[Fraction, bool]:
        """The node's start, exactly, and whether its own clock runs on the reel's frames: on the composition clock,
        a start within float noise of a frame is that frame, so a shot that starts on a reel frame keys exactly as
        its own clock's frames do."""
        start = Fraction(self.start)
        if not self.chain:
            frame = round(start * rate)
            if abs(start * rate - frame) <= _NOISE:
                return frame / rate, True
        return start, False

    def _reel(self, t: Fraction) -> Fraction:
        for origin, offset, scale in reversed(self.chain):
            o, f, s = Fraction(origin), Fraction(offset), Fraction(scale)
            t = o + f + (t - o) / s
        return t

    def _own(self, t: Fraction) -> Fraction:
        for origin, offset, scale in self.chain:
            o, f, s = Fraction(origin), Fraction(offset), Fraction(scale)
            t = o + (t - o - f) * s
        return t

    def held(self, time: float, rate: Fraction, local: bool) -> float:
        """The time, on this node's channel, to key a held change meant to show from ``time`` on it: half a frame
        before the first reel frame at or after it, never before the channel's 0. A change at 0 keys at 0.

        On a channel that runs on the reel's frames a time up to :data:`~srstudio.held_keys.SLACK` after a frame is
        that frame, a rounded frame time, as :func:`srstudio.held_keys.frame_of` reads it. On one that starts between
        them only float noise is: a time that lands a few thousandths of a frame after a reel frame is after it, and
        the engine has always shown it on the next frame, the frame it stays on."""
        if time == 0:
            return 0.0
        start, on_frames = self._start(rate) if local else (Fraction(0), not self.chain)
        reel = self._reel(Fraction(time) + start)
        frame = max(0, math.ceil(reel * rate - (Fraction(SLACK) if on_frames else _NOISE)))
        target = Fraction(2 * frame - 1, 2) / rate if frame else Fraction(0)
        return max(0.0, float(self._own(target) - start))


def clocks(composition: Any) -> dict[int, Clock]:
    """Every node under the live scene ``composition`` (an ``sr_core`` element), by ``id()`` of the node: its clock
    on the reel, with the engine's sequence placement and its groups' clocks. A timing the gate cannot follow is a
    :class:`FrameGateError`."""
    out: dict[int, Clock] = {}
    for top in (_build(_Live(c), None) for c in composition.elements() if c.xml_name not in _NOT_NODES):
        for node in _walk(top):
            chain = tuple((n.clock[0], n.clock[1], n.clock[2]) for n in _ancestors(node) if n.clock is not None)
            out[id(node.el.raw)] = Clock(node.start, chain)  # type: ignore[attr-defined]
    return out


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
