"""A reel of Rafa, the host: his plates on a sketch's clock (ADR 0068).

A sketch of his is one long appearance: the man is one frame list, so :func:`stage` draws him once and each beat's
:class:`Act` says what the cut changes, the framing, the prop under his hand and his mood. The prop and the mood change
on the same frame as the framing, :data:`CUT_LEAD` before the word, so a line never starts on the old picture. The
worktop is a foreground plate per prop, gated to its beats, and :func:`insert` lays a prop over the frame on its own.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import camera, clay, host_kit, plates, rafa, rafa_host
from .errors import SrstudioError
from .head_motion import HeadPlan
from .layout import find_engine
from .plates import Camera, Placed, Plate

__all__ = [
    "CUT_LEAD",
    "FRAMES",
    "INSERT_LENSES",
    "Act",
    "RafaReelError",
    "Renders",
    "cut",
    "framing",
    "insert",
    "insert_plate",
    "moods",
    "prop_spans",
    "stage",
]

FRAMES: dict[str, float] = {"medium": 1.0, "close": host_kit.FRAMES["close"], "tight": host_kit.FRAMES["tight"]}
CUT_LEAD = 0.05  # seconds a cut lands before its word
INSERT_LENSES: dict[str, Camera] = {  # a prop on its own, as tall as a phone: the lens is close, for its lettering
    "rafa-tote": Camera((62.0, -65.0, -196.0), (0.0, -53.0, 0.0), 40.0, 4.0),
    "rafa-mug": Camera((14.0, -30.0, -176.0), (9.0, -24.0, 0.0), 40.0, 4.0),
}
INSERT_WALL = "#3E5A52"  # the kitchen wall, so a cream prop stands off it


class RafaReelError(SrstudioError, ValueError):
    """A beat of a reel his plates cannot stage."""


@dataclass(frozen=True)
class Act:
    """What a beat shows: the ``framing``, the ``prop`` under his hand and his ``mood``."""

    framing: str
    prop: str
    mood: str

    def __post_init__(self) -> None:
        if self.framing not in FRAMES:
            raise RafaReelError(f"his framings are {tuple(FRAMES)}, got {self.framing!r}")
        if self.prop not in rafa.PROPS:
            raise RafaReelError(f"his props are {tuple(rafa.PROPS)}, got {self.prop!r}")
        if self.mood not in rafa.MOODS:
            raise RafaReelError(f"his moods are {tuple(rafa.MOODS)}, got {self.mood!r}")


@dataclass(frozen=True)
class Renders:
    """Where a reel's plates render: the engine, the cache and the fonts."""

    engine: Path
    cache: Path
    fonts: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Renders:
        """A reel's renders as its ``run`` reads them from ``env``: the engine that
        :func:`~srstudio.layout.find_engine` finds (none, or no such file, is its ``LayoutError``), the plate cache at
        ``SRSTUDIO_PLATES``, else ``plates`` beside ``SRSTUDIO_RENDERS``, and the fonts at ``SRSTUDIO_FONTS``. A missing
        setting is a :class:`RafaReelError` that names it."""
        engine = find_engine(env=env)
        if not env.get("SRSTUDIO_FONTS"):
            raise RafaReelError("set SRSTUDIO_FONTS to the folder of the installed fonts")
        if env.get("SRSTUDIO_PLATES"):
            cache = Path(env["SRSTUDIO_PLATES"])
        elif env.get("SRSTUDIO_RENDERS"):
            cache = Path(env["SRSTUDIO_RENDERS"]).parent / "plates"
        else:
            raise RafaReelError("set SRSTUDIO_RENDERS or SRSTUDIO_PLATES: the plates render into a cache")
        return cls(engine, cache, Path(env["SRSTUDIO_FONTS"]))

    def plate(self, plate: Plate) -> Path:
        return plates.render(plate, engine=self.engine, cache=self.cache, fonts=self.fonts)


def cut(at: float) -> float:
    """The frame a change meant for second ``at`` lands on: :data:`CUT_LEAD` early, never before the first frame."""
    return round(max(0.0, at - CUT_LEAD) * rafa_host.FPS) / rafa_host.FPS


def _changes(beats: Sequence[Any], acts: Sequence[Act], field: str) -> list[tuple[float, Any]]:
    if len(acts) != len(beats):
        raise RafaReelError(f"{len(acts)} acts for {len(beats)} beats")
    rows: list[tuple[float, Any]] = []
    for beat, act in zip(beats, acts, strict=True):
        value = getattr(act, field)
        if not rows or rows[-1][1] != value:
            rows.append((cut(beat.start) if rows else 0.0, value))
    return rows


def moods(beats: Sequence[Any], acts: Sequence[Act]) -> tuple[tuple[float, str], ...]:
    """His mood from the frame of each cut, as :func:`srstudio.rafa_host.faces` takes it."""
    return tuple(_changes(beats, acts, "mood"))


def prop_spans(beats: Sequence[Any], acts: Sequence[Act], end: float) -> dict[str, list[tuple[float, float]]]:
    """When each prop is under his hand: the spans run from cut to cut and leave no frame without one."""
    rows = _changes(beats, acts, "prop")
    spans: dict[str, list[tuple[float, float]]] = {}
    for (at, prop), (stop, _) in zip(rows, [*rows[1:], (end, "")], strict=True):
        spans.setdefault(prop, []).append((at, stop))
    return spans


def stage(
    acts: Sequence[Act],
    plan_of: Callable[[float], HeadPlan],
    renders: Renders,
    root: Path,
    *,
    room: str = "rafa-kitchen",
    push: tuple[float, float] = (2.4, 1.05),
) -> Callable[[Any], None]:
    """The dress of a reel: the room, him and the worktop once, in one group that pushes in over the first ``push``
    seconds, to its scale, and cuts back on the first change of framing, so the reel moves from its first frame."""

    def dress(shot: Any) -> None:
        cv, end = shot.cv, shot.end
        plan = plan_of(end)
        rows = rafa_host.faces(end, mouths=shot.mouths.get("rafa", ()), plan=plan, moods=moods(shot.beats, acts))
        made = rafa_host.sheet(rows, engine=renders.engine, cache=renders.cache, fonts=renders.fonts)
        world = cv.group(shot.back, "rafa-world")
        rafa_host.backdrop(cv, world, renders.plate(rafa_host.room(room)), root)
        rafa_host.perform(cv, world, rows, made, root, plan=plan)
        for prop, spans in prop_spans(shot.beats, acts, end).items():
            g = cv.group(world, cv.uid("rafa-prop"), opacity=0.0)
            cv.gate(g, spans)
            picture = rafa_host.worktop(renders.plate(rafa_host.foreground(prop, room)), renders.cache)
            rafa_host.front(cv, g, picture, root)
        over, to = push
        camera.anchor(world, 540.0, host_kit.PIVOT_Y, place=True)
        settle = next((cut(b.start) for b, a in zip(shot.beats, acts, strict=True) if a != acts[0]), end)
        settle = max(settle, 2.0 / rafa_host.FPS)
        keys = [(0.0, 1.0), (min(over, settle - 1.0 / rafa_host.FPS), to), (settle - 1.0 / rafa_host.FPS, to)]
        keys.append((settle, 1.0))
        for axis in ("scaleX", "scaleY"):
            cv.keys(world, axis, sorted(set(keys)), hold=False, local=False)

    return dress


def framing(acts: Sequence[Act]) -> Callable[[Any, Any], None]:
    """A ``Staging.camera``: a hold key on every change of framing, about his face (``host_kit.PIVOT_Y``)."""

    def move(shot: Any, group: Any) -> None:
        rows = _changes(shot.beats, acts, "framing")
        camera.anchor(group, 540.0, host_kit.PIVOT_Y, place=True)
        camera.zoom_holds(shot.cv, group, [(at, FRAMES[name]) for at, name in rows])

    return move


def insert(
    cv: Any, parent: Any, prop: str, start: float, end: float, renders: Renders, root: Path, id: str = ""
) -> Any:
    """``prop`` over the frame from the cut at ``start`` to the cut at ``end``. Returns its group."""
    g = cv.group(parent, id or f"{prop}-insert", start=cut(start), end=cut(end))
    rafa_host.front(cv, g, renders.plate(insert_plate(prop)), root)
    return g


def insert_plate(prop: str) -> Plate:
    """``prop`` alone, the frame's height, on the kitchen's wall."""
    if prop not in INSERT_LENSES:
        raise RafaReelError(f"the props with an insert are {tuple(INSERT_LENSES)}, got {prop!r}")
    model = clay.Model()
    rafa.PROPS[prop](model)
    meshes = tuple(rafa.finished(mesh) for mesh in model.meshes())
    used = plates.materials_of(meshes, rafa.materials())
    lights = plates.stage_lights()
    return Plate(rafa_host.WIDTH, rafa_host.HEIGHT, INSERT_LENSES[prop], lights, (Placed(meshes),), used, INSERT_WALL)
