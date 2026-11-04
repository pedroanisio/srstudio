"""Small Print's explainer shots: the finding acted out in 3D on Rafa's worktop, close up (ADR 0240).

A :class:`Shot` takes the frame for a run of beats, as a v1 paper panel did, and holds the v2 bar as checks that fail:

1. **Same world as the host.** Three plates through one lens and one light: his room, thrown out of focus; the shot's
   still part (``still``, on his worktop); and its moving parts (``pose`` of a moment, drawn by ``draw``), one plate
   every :data:`STEP` frames, as his own face is a plate a frame.
2. **The subject fills the frame.** :func:`share` measures what the shot draws (``still`` and the moving parts, not
   the worktop or the room) as a share of the frame, through the lens and the camera's move; it stays at
   :data:`SHARE` or more, and :func:`empty_band` (rows it leaves bare: worktop, wall) at :data:`BAND` or less.
3. **Motion every 1-2 s.** :func:`longest_still` is the longest run of frames on which nothing moves by
   :data:`STILL_PX` or more and no part changes; it stays under :data:`STILL_FOR`.
4. **Real detail** is the parts' own (:mod:`srstudio.smallprint_lab`).
5. **Typography with hierarchy.** Two text layers at most with the captions: one short :attr:`Shot.headline` in a
   paper chip at the top until the stamp lands, then the stamp in its place with its source in a smaller chip under
   it. :func:`clashes` lists every word that touches another or a printed face the lens sees (a dial, a page).

:func:`check` runs them all before a plate is rendered, so a shot that fails the bar never costs a render.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

import numpy as np
from PIL import Image, ImageDraw

from . import look, plates, rafa, rafa_host
from .clay import Mesh, Model
from .ink_meter import LEGIBLE_PX
from .layout import VERTICAL
from .plates import Camera, Light, Material, Placed, Plate
from .rafa_reel import Renders
from .smallprint_kit import (
    INK,
    LEFT,
    PAPER,
    RIGHT,
    Measure,
    ScriptError,
    Stamp,
    label,
    source_chip,
    stamp,
    stamp_layout,
)

__all__ = [
    "FPS",
    "HEADLINE_SIZE",
    "SHARE",
    "STEP",
    "STILL_FOR",
    "STILL_PX",
    "SAFE_TOP",
    "Box",
    "Move",
    "Shot",
    "BAND",
    "camera_at",
    "check",
    "clashes",
    "draw",
    "empty_band",
    "words",
    "frames",
    "headline_box",
    "longest_still",
    "printed_boxes",
    "room_plate",
    "share",
    "stamp_time",
    "still_plate",
    "moving_plate",
]

FPS = rafa_host.FPS
STEP = 2  # frames a moving plate holds: on twos, as stop motion is shot
SHARE = 1.0 / 3.0  # the least of the frame the subject covers
STILL_FOR = 1.5  # seconds: no run of frames without motion as long as this (craft audit C4)
STILL_PX = 2.0  # a move smaller than this, in frame pixels at the frame's edge, is not motion
SCALE = 1.25  # plates render this much larger than the frame, so a push-in stays sharp
ROOM_BLUR = 9.0  # px: his room behind a close-up is further out of focus than behind him
PARALLAX = 0.45  # how much of the camera's move the room makes
HEADLINE_SIZE, HEAD_Y, HEAD_PAD = 54.0, 236.0, 22.0
STAMP_TOP = HEAD_Y  # the stamp takes the headline's place when it lands: never three words on screen with the captions
TOP_ROW, LOW_ROW = HEAD_Y, 1052.0  # the rows a stamp's top may be at: its source chip stays clear of the caption band
BAND = 0.2  # the tallest share of the frame's rows the subject may leave bare (craft audit C1)
BAND_FILL = 0.1  # a row the subject covers less of than this is bare
CLEAR_PX = 12.0  # the least gap between two words on screen
MASK = 4  # the share is measured on a raster this many times coarser than the frame
W, H = rafa_host.WIDTH, rafa_host.HEIGHT
SAFE_TOP = VERTICAL.region(W, H).y0  # the top of the reel's safe area: no word above it, landing or landed

Box = tuple[float, float, float, float]  # x0, y0, x1, y1 in frame pixels


@dataclass(frozen=True)
class Move:
    """A key of the camera at second ``at`` on the reel's clock: ``zoom`` about the shot's pivot, then moved ``dx``,
    ``dy`` frame pixels. Between keys it eases in and out."""

    at: float
    zoom: float = 1.0
    dx: float = 0.0
    dy: float = 0.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.at, self.zoom, self.dx, self.dy)):
            raise ScriptError(f"a camera key is numbers, got {self}")
        if not 1.0 <= self.zoom <= SCALE:
            raise ScriptError(f"the camera zooms 1 to {SCALE} (the plates' own size), got {self.zoom}")


@dataclass(frozen=True)
class Shot:
    """One explainer shot. ``panel`` names the beats' panel it draws; ``lens`` sees his worktop; ``headline`` is the
    one short line over it. ``still`` draws what stands still, ``pose(t)`` is what the moving parts are doing at second
    ``t`` of the reel (any hashable value: equal poses are one plate) and ``draw(m, pose)`` draws them. ``palette`` and
    ``finish`` are the parts' materials and surface. ``moves`` key the camera about ``pivot``; ``stamp_at`` is the
    second the stamp lands, on the word that says it, or None for :data:`STAMP_LEAD` after its line starts.
    ``printed`` names the materials that carry lettering, which no word on screen may touch, and ``lamps`` are the
    subject's own lights. ``stamp_top`` is the stamp's top row: the headline's place by default."""

    panel: str
    lens: Camera
    headline: str
    still: Callable[[Model], None]
    pose: Callable[[float], Hashable]
    draw: Callable[[Model, Any], None]
    palette: Callable[[], Mapping[str, Material]]
    finish: Callable[[Mesh], Mesh]
    moves: tuple[Move, ...] = (Move(0.0),)
    pivot: tuple[float, float] = (W / 2, H / 2)
    stamp_at: float | None = None
    room: str = "rafa-kitchen"
    printed: frozenset[str] = field(default_factory=frozenset)  # materials whose print is lettering
    lamps: tuple[Light, ...] = ()  # the subject's own lights, as a tank's lamp, added to his worktop's
    stamp_top: float = STAMP_TOP  # where the stamp lands: in the headline's place, or low when the top is busy

    def __post_init__(self) -> None:
        if not self.panel or not self.headline.strip():
            raise ScriptError(f"a shot names its panel and has a headline, got {self.panel!r}, {self.headline!r}")
        if len(self.headline) > 26 or self.headline != self.headline.upper():
            raise ScriptError(f"{self.panel}: a headline is short, 26 capitals at most, got {self.headline!r}")
        if not self.moves or [m.at for m in self.moves] != sorted(m.at for m in self.moves):
            raise ScriptError(f"{self.panel}: the camera's keys go forward in time")
        if not TOP_ROW <= self.stamp_top <= LOW_ROW:
            raise ScriptError(f"{self.panel}: a stamp lands from row {TOP_ROW} to {LOW_ROW}, got {self.stamp_top}")
        if self.room not in rafa.ROOMS:
            raise ScriptError(f"{self.panel}: his rooms are {tuple(rafa.ROOMS)}, got {self.room!r}")


STAMP_LEAD = 0.35


# -- the camera -------------------------------------------------------------------------------------------------------
def _ease(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, u)))


def camera_at(shot: Shot, t: float) -> tuple[float, float, float]:
    """The camera's (zoom, dx, dy) at second ``t``, eased between its keys as the engine eases them."""
    keys = shot.moves
    if t <= keys[0].at:
        k = keys[0]
        return k.zoom, k.dx, k.dy
    for a, b in zip(keys, keys[1:], strict=False):
        if a.at <= t <= b.at:
            u = _ease((t - a.at) / (b.at - a.at)) if b.at > a.at else 1.0
            return a.zoom + (b.zoom - a.zoom) * u, a.dx + (b.dx - a.dx) * u, a.dy + (b.dy - a.dy) * u
    k = keys[-1]
    return k.zoom, k.dx, k.dy


def _seen(shot: Shot, points: np.ndarray, t: float) -> np.ndarray:
    """Frame pixels of scene ``points`` through the lens and the camera at ``t``."""
    flat = rafa_host.project(points, lens=shot.lens, width=W, height=H)
    zoom, dx, dy = camera_at(shot, t)
    px, py = shot.pivot
    return np.stack((px + (flat[:, 0] - px) * zoom + dx, py + (flat[:, 1] - py) * zoom + dy), axis=1)


# -- the frames -------------------------------------------------------------------------------------------------------
def frames(shot: Shot, first: float, last: float) -> list[tuple[float, Hashable]]:
    """Every frame of the shot from ``first`` to ``last``: its second and the pose of its plate, which changes every
    :data:`STEP` frames."""
    n = max(1, round((last - first) * FPS))
    rows = []
    for k in range(n):
        held = first + (k - k % STEP) / FPS
        rows.append((first + k / FPS, shot.pose(held)))
    return rows


def _meshes(build: Callable[[Model], None], finish: Callable[[Mesh], Mesh]) -> tuple[Mesh, ...]:
    m = Model()
    build(m)
    return tuple(finish(mesh) for mesh in m.meshes())


@lru_cache(maxsize=16)
def _still(shot: Shot) -> tuple[Mesh, ...]:
    return _meshes(shot.still, shot.finish)


def _moving(shot: Shot, pose: Hashable) -> tuple[Mesh, ...]:
    return _meshes(lambda m: shot.draw(m, pose), shot.finish)


def subject(shot: Shot, pose: Hashable) -> tuple[Mesh, ...]:
    """What the shot explains at ``pose``: its still part and its moving parts, not his worktop or his room."""
    return (*_still(shot), *_moving(shot, pose))


def _raster(shot: Shot, meshes: Sequence[Mesh]) -> Image.Image:
    mask = Image.new("L", (W // MASK, H // MASK), 0)
    pen = ImageDraw.Draw(mask)
    for mesh in meshes:
        pixels = rafa_host.project(mesh.vertices, lens=shot.lens, width=W, height=H) / MASK
        for tri in mesh.triangles:
            pen.polygon([tuple(p) for p in pixels[tri]], fill=255)
    return mask


@lru_cache(maxsize=16)
def _still_mask(shot: Shot) -> Image.Image:
    return _raster(shot, _still(shot))


def _seen_mask(shot: Shot, t: float, pose: Hashable | None) -> np.ndarray:
    """Where the subject is in the frame at ``t``: every triangle of it through the lens, on a raster :data:`MASK`
    times coarser than the frame, moved as the camera moves the plates."""
    pose = shot.pose(t) if pose is None else pose
    mask = Image.fromarray(np.maximum(np.asarray(_still_mask(shot)), np.asarray(_raster(shot, _moving(shot, pose)))))
    zoom, dx, dy = camera_at(shot, t)
    px, py = shot.pivot[0] / MASK, shot.pivot[1] / MASK
    # a frame point q shows the plate's point pivot + (q - pivot - d) / zoom
    back = (1 / zoom, 0.0, px - (px + dx / MASK) / zoom, 0.0, 1 / zoom, py - (py + dy / MASK) / zoom)
    seen = mask.transform(mask.size, Image.Transform.AFFINE, back, resample=Image.Resampling.NEAREST)
    return np.asarray(seen) > 127


def share(shot: Shot, t: float, pose: Hashable | None = None) -> float:
    """The share of the frame the subject covers at second ``t``."""
    return float(_seen_mask(shot, t, pose).mean())


def empty_band(shot: Shot, t: float, pose: Hashable | None = None, words: Sequence[Box] = ()) -> float:
    """The tallest run of the frame's rows that neither the subject nor the ``words`` on screen cover at ``t``
    (covering under :data:`BAND_FILL` of the row), as a share of the frame's height: a band of worktop or wall with
    nothing being explained in it. A row the headline or the stamp crosses carries words, so it is not bare."""
    seen = _seen_mask(shot, t, pose).copy()
    for x0, y0, x1, y1 in words:
        seen[
            max(0, round(y0 / MASK)) : max(0, round(y1 / MASK)), max(0, round(x0 / MASK)) : max(0, round(x1 / MASK))
        ] = True
    bare = seen.mean(axis=1) < BAND_FILL
    longest = run = 0
    for row in bare:
        run = run + 1 if row else 0
        longest = max(longest, run)
    return longest / len(bare)


def longest_still(shot: Shot, first: float, last: float) -> float:
    """The longest run of frames, in seconds, on which no part changes and the camera moves nothing at the frame's
    edge by :data:`STILL_PX` or more."""
    corners = np.array([[0.0, 0.0], [W, 0.0], [0.0, H], [W, H]])

    def edge(t: float) -> np.ndarray:
        zoom, dx, dy = camera_at(shot, t)
        px, py = shot.pivot
        return np.stack((px + (corners[:, 0] - px) * zoom + dx, py + (corners[:, 1] - py) * zoom + dy), axis=1)

    rows = frames(shot, first, last)
    longest, start = 0.0, 0
    for k in range(1, len(rows) + 1):
        moved = k == len(rows) or rows[k][1] != rows[start][1]
        if not moved:
            moved = float(np.abs(edge(rows[k][0]) - edge(rows[start][0])).max()) >= STILL_PX
        if moved:
            longest = max(longest, (k - start) / FPS)
            start = k
    return longest


# -- the words --------------------------------------------------------------------------------------------------------
def headline_box(shot: Shot, measure: Measure) -> Box:
    """The headline's chip: one line at :data:`HEADLINE_SIZE`, at the top left of the safe area."""
    wide = measure(shot.headline, HEADLINE_SIZE) + 2 * HEAD_PAD
    if wide > RIGHT - LEFT:
        raise ScriptError(f"{shot.panel}: {shot.headline!r} is wider than the safe area at {HEADLINE_SIZE}")
    return (LEFT, HEAD_Y, LEFT + wide, HEAD_Y + HEADLINE_SIZE * 1.35 + 2 * HEAD_PAD * 0.6)


def printed_boxes(shot: Shot, t: float, pose: Hashable | None = None) -> list[tuple[str, Box]]:
    """Every printed face the lens sees at ``t`` (its lettering): the frame box each one covers."""
    out = []
    for mesh in subject(shot, shot.pose(t) if pose is None else pose):
        if mesh.material in shot.printed:
            p = _seen(shot, mesh.vertices, t)
            out.append((mesh.material, (float(p[:, 0].min()), float(p[:, 1].min()), float(p[:, 0].max()),
                                        float(p[:, 1].max()))))  # fmt: skip
    return out


def _touch(a: Box, b: Box, gap: float = CLEAR_PX) -> bool:
    return a[0] - gap < b[2] and b[0] - gap < a[2] and a[1] - gap < b[3] and b[1] - gap < a[3]


def stamp_time(shot: Shot, said: float | None, first: float) -> float:
    """When the stamp lands: on the shot's word when it names one, else :data:`STAMP_LEAD` after its line starts
    (``said``), never before the shot's ``first`` frame."""
    if shot.stamp_at is not None:
        return max(first, shot.stamp_at)
    return max(first, (first if said is None else said) + STAMP_LEAD)


def words(shot: Shot, stamped: Stamp | None, landed: float, measure: Measure) -> list[tuple[str, Box, float, float]]:
    """The shot's words on screen as (name, frame box, from, until): the headline until ``landed``, then the stamp
    and the paper chip its source rows sit on."""
    head = headline_box(shot, measure)
    if stamped is None:
        return [("headline", head, -math.inf, math.inf)]
    _, box, sources, _ = stamp_layout(stamped, measure, shot.stamp_top)
    return [("headline", head, -math.inf, landed), ("stamp", box, landed, math.inf),
            *([("source", source_chip(sources), landed, math.inf)] if sources else [])]  # fmt: skip


def clashes(shot: Shot, stamped: Stamp | None, landed: float, measure: Measure, times: Sequence[float]) -> list[str]:
    """Every word on screen that touches a printed face of the subject at the seconds ``times``, with
    :data:`CLEAR_PX` between them: the headline until ``landed``, then the stamp and its source."""
    found = []
    on = words(shot, stamped, landed, measure)
    for t in times:
        for name, box in printed_boxes(shot, t):
            for word, at, since, until in on:
                if since <= t < until and _touch(box, at):
                    found.append(f"{shot.panel}: at {t:.2f} s the {name} touches the {word}")
    return sorted(set(found))


def check(shot: Shot, first: float, last: float, stamped: Stamp | None, measure: Measure, *, said: float | None = None,
          every: int = 3) -> None:  # fmt: skip
    """The bar on the shot from ``first`` to ``last``, or :class:`ScriptError` naming every miss: the subject's
    share and the bare band on every ``every``-th plate and the last, the longest still, the words that touch, and a
    stamp up long enough to read."""
    misses = []
    rows = frames(shot, first, last)
    picked = [*rows[:: STEP * every], rows[-1]]
    landed = stamp_time(shot, said, first)
    on = words(shot, stamped, landed, measure)
    for t, pose in picked:
        got = share(shot, t, pose)
        if got < SHARE:
            misses.append(f"{shot.panel}: at {t:.2f} s the subject covers {got:.0%} of the frame, under {SHARE:.0%}")
        bare = empty_band(shot, t, pose, [box for _, box, since, until in on if since <= t < until])
        if bare > BAND:
            misses.append(f"{shot.panel}: at {t:.2f} s a bare band {bare:.0%} of the frame tall, over {BAND:.0%}")
    still = longest_still(shot, first, last)
    if still >= STILL_FOR:
        misses.append(f"{shot.panel}: nothing moves for {still:.2f} s")
    misses += clashes(shot, stamped, landed, measure, [t for t, _ in picked])
    if stamped is not None and last - landed < READ_FOR:
        misses.append(f"{shot.panel}: the stamp is up {last - landed:.2f} s, under {READ_FOR} s")
    if misses:
        raise ScriptError("; ".join(misses))


READ_FOR = 0.8333  # seconds a stamp stays up at the least: as long as a panel's own words


# -- the plates and the drawing ---------------------------------------------------------------------------------------
def _size() -> tuple[int, int]:
    return round(W * SCALE), round(H * SCALE)


def _plate(shot: Shot, meshes: Sequence[Mesh], *, lights, background: str = plates.CLEAR, samples: int = 48) -> Plate:
    palette = dict(shot.palette())
    return Plate(*_size(), shot.lens, lights, (Placed(tuple(meshes)),), plates.materials_of(meshes, palette),
                 background, samples)  # fmt: skip


def room_plate(shot: Shot) -> Plate:
    """His room through the shot's lens, lit as his room plate is."""
    meshes = _meshes(rafa.ROOMS[shot.room], rafa.finished)
    lights = plates.stage_lights(warm=shot.room == "rafa-kitchen", room=True, rim=False)
    return _plate(shot, meshes, lights=lights, background="#E6D8C0")


def _worktop_lights(shot: Shot) -> tuple[Light, ...]:
    return (*plates.stage_lights(warm=True, room=False, rim=True), *shot.lamps)  # as his worktop plates are lit


def still_plate(shot: Shot) -> Plate:
    """His worktop with the shot's still part on it, on clear."""
    tops = rafa_host.ROOM_TOPS[shot.room]
    meshes = (*_meshes(lambda m: rafa.counter(m, *tops), rafa.finished), *_meshes(shot.still, shot.finish))
    return _plate(shot, meshes, lights=_worktop_lights(shot))


def moving_plate(shot: Shot, pose: Hashable) -> Plate:
    """The moving parts at ``pose`` on clear, to lay over :func:`still_plate`."""
    return _plate(shot, _meshes(lambda m: shot.draw(m, pose), shot.finish), lights=_worktop_lights(shot))


def _scaled(cv, parent, name: str):
    """A group that draws a plate of :func:`_size` at the frame's size."""
    return cv.group(parent, cv.uid(name), scaleX=1.0 / SCALE, scaleY=1.0 / SCALE)


def _camera(cv, g, shot: Shot, amount: float) -> None:
    px, py = shot.pivot
    zooms = [(m.at, 1.0 + (m.zoom - 1.0) * amount) for m in shot.moves]
    for axis in ("scaleX", "scaleY"):
        cv.keys(g, axis, zooms, hold=False, kind="sine-in-out", local=False)
    cv.keys(g, "x", [(m.at, px + m.dx * amount) for m in shot.moves], hold=False, kind="sine-in-out", local=False)
    cv.keys(g, "y", [(m.at, py + m.dy * amount) for m in shot.moves], hold=False, kind="sine-in-out", local=False)


_SHELVES: WeakKeyDictionary[Any, rafa_host._Shelf] = WeakKeyDictionary()


def _shelf(cv, root: Path) -> rafa_host._Shelf:
    """One shelf of picture files a document, so shots that share a plate (one lens, one room) add it once."""
    shelf = _SHELVES.get(cv)
    if shelf is None or shelf.folder != root / "assets" / "rafa":
        shelf = _SHELVES[cv] = rafa_host._Shelf(cv, root)
    return shelf


def draw(cv, parent, shot: Shot, first: float, last: float, renders: Renders, root: Path, measure: Measure,
         stamped: Stamp | None = None, said: float | None = None) -> Any:  # fmt: skip
    """The shot over the frame from ``first`` to ``last``: his room out of focus, his worktop with the still part,
    the moving parts a plate every :data:`STEP` frames, the camera's move with the room moving less than the worktop,
    the headline, and the stamp on its word. Checks the bar first. Returns the shot's group."""
    check(shot, first, last, stamped, measure, said=said)
    shelf = _shelf(cv, Path(root))
    w, h = _size()
    g = cv.group(parent, cv.uid(f"smallprint-scene-{shot.panel}"), start=first, end=last)
    cv.rect(g, 0, 0, W, H, "#5F8579")
    px, py = shot.pivot
    far = cv.group(g, f"{shot.panel}-room-angle", x=px, y=py, anchorX=px, anchorY=py)
    _camera(cv, far, shot, PARALLAX)
    blurred = look.depth(cv, far, f"smallprint-room-{shot.panel}", ROOM_BLUR, moving=True)
    room = shelf.name(renders.plate(room_plate(shot)), w, h)
    _scaled(cv, blurred, "sp-room").add_layer(id=cv.uid("sp-room-layer"), asset=room, x=0, y=0)
    near = cv.group(g, f"{shot.panel}-bench-angle", x=px, y=py, anchorX=px, anchorY=py)
    _camera(cv, near, shot, 1.0)
    bench = _scaled(cv, near, "sp-bench")
    bench.add_layer(id=cv.uid("sp-bench-layer"), asset=shelf.name(renders.plate(still_plate(shot)), w, h), x=0, y=0)
    spans: dict[Hashable, list[tuple[float, float]]] = {}
    for t, pose in frames(shot, first, last):
        rows = spans.setdefault(pose, [])
        if rows and math.isclose(rows[-1][1], t, abs_tol=1e-6):
            rows[-1] = (rows[-1][0], t + 1.0 / FPS)
        else:
            rows.append((t, t + 1.0 / FPS))
    for pose, runs in spans.items():
        layer = cv.group(bench, cv.uid("sp-part"), opacity=0.0)
        cv.gate(layer, runs)
        layer.add_layer(id=cv.uid("sp-part-layer"), asset=shelf.name(renders.plate(moving_plate(shot, pose)), w, h),
                        x=0, y=0)  # fmt: skip
    landed = stamp_time(shot, said, first) if stamped is not None else last
    _headline(cv, g, shot, first, landed, measure)
    if stamped is not None:
        stamp(cv, g, stamped, landed, last, measure, top=shot.stamp_top, chip=True, ceiling=SAFE_TOP)
    return g


def _headline(cv, g, shot: Shot, first: float, last: float, measure: Measure) -> None:
    x0, y0, x1, y1 = headline_box(shot, measure)
    chip = cv.group(g, cv.uid("smallprint-headline"), start=first, end=last, x=x0, y=y0, anchorX=x0, anchorY=y0)
    cv.rect(chip, x0 + 6, y0 + 8, x1 - x0, y1 - y0, "#00000040", radius=16.0)
    cv.rect(chip, x0, y0, x1 - x0, y1 - y0, PAPER, stroke=INK, sw=4.0, radius=16.0)
    label(cv, chip, shot.headline, x0, y0, x1 - x0, y1 - y0, HEADLINE_SIZE, INK, "center")
    cv.pop_in(chip, first + 0.05, from_=0.9, over=1.03)
    cv.keys(chip, "opacity", [(first, 0.0), (first + 0.08, 1.0)], hold=False, local=False)


assert LEGIBLE_PX < 30.0 < HEADLINE_SIZE  # the source is the smallest word on screen, and still legible
