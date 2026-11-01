"""A rigid object drawn from a 3D proxy, the default for anything rigid seen from more than one angle (ADR 0091).

A model from :mod:`srstudio.clay` goes through :mod:`srstudio.plates` twice for one :class:`View`: a light pass and a
pass of flat part colours. The light is cut into soft tone bands per part by a :class:`Recipe`, and ink runs where parts
meet, so a multicoloured object keeps its paint under any light and every angle of it is the same drawing.

:func:`layers` splits the picture for compositing: ``back`` is drawn under the people, ``front`` over them, and
``under`` beneath both, for what stays put while the body moves (a car's tyres). :meth:`View.project` and
:meth:`View.disc` place 2D drawings on the model, with the camera that drew it; both fit a stationary view, so a moved
camera is a new view and new plates.

Everything a render would trip over is refused first, with a :class:`ProxyError`, and nothing reaches the engine or the
cache. A plate's pixels are deterministic for its inputs, and a warm rebuild renders nothing.
"""

from __future__ import annotations

import dataclasses
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import checks, plates
from .clay import Mesh
from .errors import SrstudioError

__all__ = ["Disc", "ID_GAIN", "Ink", "Layers", "ProxyError", "Recipe", "View", "composite", "layers", "picture"]
__all__ += ["read_parts", "rgb", "split"]

Tones = tuple[str, str, str, str]
_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
_LATTICE = [(r, g, b) for r in (30, 80, 130, 180) for g in (30, 80, 130, 180) for b in (30, 80, 130, 180)]
ID_GAIN = 1.04  # the engine's lift on an emissive colour, measured on plates
_LIGHTS = (
    plates.Light("key", "directional", "#ffffff", 1.15, yaw=-35, pitch=-52),
    plates.Light("fill", "ambient", "#ffffff", 0.32),
)


class ProxyError(SrstudioError, ValueError):
    """A view, a recipe or a set of meshes that cannot make plates."""


def rgb(colour: str) -> np.ndarray:
    return np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)], float) / 255


@dataclass(frozen=True)
class Disc:
    """A flat circle as 2D groups draw it: at (x, y) on the frame, turned ``tilt``, scaled ``stretch`` by ``squash``,
    then turned ``turn`` inside that, in degrees and px per scene unit."""

    x: float
    y: float
    tilt: float
    stretch: float
    squash: float
    turn: float


@dataclass(frozen=True)
class View:
    """One stationary camera on a model. ``fov`` is horizontal in degrees, ``stretch`` scales the model along x before
    it is seen (a flat cartoon's cheat), and ``size`` is the final frame in px."""

    position: tuple[float, float, float]
    target: tuple[float, float, float]
    fov: float
    stretch: float = 1.0
    size: tuple[int, int] = (1080, 1920)

    def __post_init__(self) -> None:
        if not (checks.number(self.fov) and 0 < self.fov < 180):
            raise ProxyError(f"a lens of {self.fov} degrees cannot exist")
        if not (checks.number(self.stretch) and self.stretch > 0):
            raise ProxyError(f"stretch {self.stretch} must be above zero")
        width, height = self.size
        if width <= 0 or height <= 0 or width % 2 or height % 2:
            raise ProxyError(f"frame {self.size} must be positive and even")
        if np.allclose(self.position, self.target):
            raise ProxyError(f"a camera at {self.position} looks at itself")

    @cached_property
    def _axes(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        forward = np.subtract(self.target, self.position)
        forward = forward / np.linalg.norm(forward)
        right = np.cross((0, 1, 0), forward)
        length = np.linalg.norm(right)
        if length < 1e-9:
            raise ProxyError(f"a camera looking straight along y has no right: {self.position} to {self.target}")
        right = right / length
        return forward, right, np.cross(forward, right), self.size[0] / 2 / math.tan(math.radians(self.fov) / 2)

    def project(self, points: Iterable[Sequence[float]]) -> np.ndarray:
        """Scene points on the final frame, in px. A point at or behind the lens is refused."""
        forward, right, down, focal = self._axes
        ray = np.asarray(list(points), float) * (self.stretch, 1, 1) - np.array(self.position)
        depth = ray @ forward
        if depth.min() <= 0:
            raise ProxyError(f"a point is behind the lens of the camera at {self.position}")
        width, height = self.size
        return np.stack([width / 2 + focal * (ray @ right) / depth, height / 2 + focal * (ray @ down) / depth], 1)

    def disc(self, centre: Sequence[float], radius: float, facing: int) -> Disc | None:
        """A circle upright in a plane of constant z, its face toward ``facing`` on z, or None when that face turns
        from the lens, it stands behind the lens or it misses the frame. A long lens lets a skew (two turns and a
        scale), fitted across the full width, stand in for the projection; a face seen from the far side is mirrored,
        which no turn can show, so a rim drawn on it has to look the same either way round."""
        if not (checks.number(radius) and radius > 0):
            raise ProxyError(f"a disc needs a radius above zero, got {radius}")
        x, y, z = centre
        if (self.position[2] - z) * facing <= 0:
            return None
        rim = [(x + radius, y, z), (x - radius, y, z), (x, y + radius, z), (x, y - radius, z)]
        if ((np.array(rim) * (self.stretch, 1, 1) - self.position) @ self._axes[0]).min() <= 0:
            return None
        ahead, behind, under, over = self.project(rim)
        middle = (ahead + behind + under + over) / 4
        turns, scales, unturns = np.linalg.svd(np.column_stack([ahead - behind, under - over]) / (2 * radius))
        if np.linalg.det(turns) < 0:
            turns[:, 1] *= -1
            unturns[1] *= -1
        reach = radius * scales[0]
        if not (-reach < middle[0] < self.size[0] + reach and -reach < middle[1] < self.size[1] + reach):
            return None
        tilt = math.degrees(math.atan2(turns[1, 0], turns[0, 0]))
        turn = math.degrees(math.atan2(unturns[1, 0], unturns[0, 0]))
        return Disc(float(middle[0]), float(middle[1]), tilt, float(scales[0]), float(scales[1]), turn)


@dataclass(frozen=True)
class Ink:
    """The line: weights in px on the final frame, ``grain`` its wander, ``shade`` its thickening on the dark side."""

    colour: str = "#26303a"
    weight: float = 0.8
    grain: float = 0.2
    shade: float = 0.5
    least: float = 0.6
    most: float = 2.0

    def __post_init__(self) -> None:
        if not _HEX.match(self.colour):
            raise ProxyError(f"ink {self.colour!r} must be #rrggbb")
        widths = (self.weight, self.grain, self.shade, self.least, self.most)
        if not (all(checks.number(w) and w >= 0 for w in widths) and self.least <= self.most):
            raise ProxyError(f"ink widths {widths} must not be negative, least no more than most")


@dataclass(frozen=True)
class Recipe:
    """A style's conversion. ``tones`` gives each part shade to highlight; ``quiet`` groups parts that meet with no
    line between them; ``behind`` is what the people stand in front of; ``under`` goes on a plate of its own."""

    tones: Mapping[str, Tones]
    quiet: tuple[tuple[str, ...], ...] = ()
    behind: frozenset[str] = frozenset()
    under: frozenset[str] = frozenset()
    rough: Mapping[str, float] = field(default_factory=dict)
    lights: tuple[plates.Light, ...] = _LIGHTS
    ink: Ink = Ink()
    thresholds: tuple[float, float, float] = (0.365, 0.475, 0.565)
    soft_edge: float = 0.07
    oversample: int = 2
    grain_seed: int = 7

    def __post_init__(self) -> None:
        if not 1 <= len(self.tones) <= len(_LATTICE):
            raise ProxyError(f"a recipe draws 1 to {len(_LATTICE)} parts, got {len(self.tones)}")
        for name, tones in self.tones.items():
            if len(tones) != 4 or not all(_HEX.match(c) for c in tones):
                raise ProxyError(f"part {name} needs four #rrggbb tones, got {tones!r}")
        for what, names in (("behind", self.behind), ("under", self.under), *(("quiet", g) for g in self.quiet)):
            stray = sorted(set(names) - set(self.tones))
            if stray:
                raise ProxyError(f"{what} names parts with no tones: {stray}")
        families = [name for group in self.quiet for name in set(group)]
        shared = sorted({name for name in families if families.count(name) > 1})
        if shared:
            raise ProxyError(f"quiet groups share {shared}: each part keeps one family")
        stray = sorted(set(self.rough) - set(self.tones))
        if stray:
            raise ProxyError(f"rough names parts with no tones: {stray}")
        if not all(checks.number(r) and 0 <= r <= 1 for r in self.rough.values()):
            raise ProxyError(f"roughness {dict(self.rough)} must be between 0 and 1")
        rising = all(map(checks.number, self.thresholds)) and list(self.thresholds) == sorted(self.thresholds)
        if not rising or len(set(self.thresholds)) != 3:
            raise ProxyError(f"thresholds {self.thresholds} must rise")
        if not (checks.number(self.soft_edge) and self.soft_edge >= 0):
            raise ProxyError(f"soft_edge {self.soft_edge} must not be negative")
        if not isinstance(self.oversample, int) or self.oversample < 1:
            raise ProxyError(f"oversample {self.oversample} must be a whole number from 1")

    @property
    def names(self) -> list[str]:
        return sorted(self.tones)

    @property
    def ids(self) -> dict[str, tuple[int, int, int]]:
        """Each part's flat colour: unsaturated, so tone mapping spares it."""
        return {name: _LATTICE[(i * 37 + 5) % len(_LATTICE)] for i, name in enumerate(self.names)}


@dataclass(frozen=True)
class Layers:
    """A view's plates as RGBA bytes. ``under`` is None for a recipe that keeps nothing under."""

    back: np.ndarray
    front: np.ndarray
    under: np.ndarray | None

    def write(self, folder: Path, stem: str) -> None:
        """``stem-back.png``, ``stem-front.png`` and, when it has one, ``stem-under.png``."""
        folder.mkdir(parents=True, exist_ok=True)
        plates.write_png(folder / f"{stem}-back.png", self.back)
        plates.write_png(folder / f"{stem}-front.png", self.front)
        if self.under is not None:
            plates.write_png(folder / f"{stem}-under.png", self.under)


def _smooth(a: float, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _plate(view: View, meshes: Sequence[Mesh], recipe: Recipe, flat: bool) -> plates.Plate:
    ids, names = recipe.ids, recipe.names
    if flat:
        materials = tuple(plates.Material(n, "#000000", emissive="#{:02x}{:02x}{:02x}".format(*ids[n])) for n in names)
        lights: tuple[plates.Light, ...] = (plates.Light("nil", "ambient", "#000000", 0.0),)
    else:
        materials = tuple(plates.Material(n, "#9a9a9a", roughness=recipe.rough.get(n, 0.6)) for n in names)
        lights = recipe.lights
    width, height = view.size
    camera = plates.Camera(view.position, view.target, view.fov, 10)
    size = recipe.oversample
    return plates.Plate(width * size, height * size, camera, lights, (plates.Placed(tuple(meshes)),), materials)


def read_parts(ids: np.ndarray, recipe: Recipe) -> np.ndarray:
    """Each pixel's part index, -1 on empty pixels. An edge pixel blended into a third part's colour is dropped by a
    3x3 opening and refilled from the nearest kept pixel."""
    names = recipe.names
    table = np.array([recipe.ids[n] for n in names], float) * ID_GAIN
    part = ((ids[..., :3].astype(float)[..., None, :] - table) ** 2).sum(-1).argmin(-1)
    part[ids[..., 3] < 128] = -1
    keep = part < 0
    for k in range(len(names)):
        mask = part == k
        if mask.any():
            keep |= ndimage.binary_opening(mask, np.ones((3, 3), bool))
    nearest = ndimage.distance_transform_edt(~keep, return_distances=False, return_indices=True)
    return part[tuple(nearest)]


def _edges(labels: np.ndarray) -> np.ndarray:
    edge = np.zeros(labels.shape, bool)
    edge[:-1] |= labels[:-1] != labels[1:]
    edge[1:] |= labels[:-1] != labels[1:]
    edge[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    edge[:, 1:] |= labels[:, :-1] != labels[:, 1:]
    return edge


def _bands(part: np.ndarray, luma: np.ndarray, recipe: Recipe) -> np.ndarray:
    out = np.zeros((*part.shape, 3))
    for k, name in enumerate(recipe.names):
        mask = part == k
        if not mask.any():
            continue
        shade, *tones = [rgb(c) for c in recipe.tones[name]]
        colour = shade[None] * np.ones((mask.sum(), 3))
        for tone, threshold in zip(tones, recipe.thresholds, strict=True):
            t = _smooth(threshold - recipe.soft_edge, threshold + recipe.soft_edge, luma[mask])[:, None]
            colour = colour * (1 - t) + tone * t
        out[mask] = colour
    return out


def composite(lit: np.ndarray, ids: np.ndarray, recipe: Recipe) -> tuple[np.ndarray, np.ndarray]:
    """Colour and ink from a light pass and a part pass: the RGBA picture and each pixel's part."""
    part = read_parts(ids, recipe)
    if part.max() < 0:
        raise ProxyError("nothing of the model falls in the frame")
    height, width = part.shape
    names = recipe.names
    luma = ndimage.gaussian_filter(lit[..., :3].mean(-1) / 255.0, 1.2)
    out = _bands(part, luma, recipe)
    family = np.arange(len(names) + 1)
    for group in recipe.quiet:
        ks = [names.index(n) for n in group]
        family[ks] = ks[0]
    labels = family[part]
    labels[part < 0] = len(names)
    edges = _edges(labels)
    distance = ndimage.distance_transform_edt(~edges) if edges.any() else np.full(edges.shape, np.inf)
    noise = np.random.default_rng(recipe.grain_seed).standard_normal((height // 4 + 1, width // 4 + 1))
    grain = ndimage.gaussian_filter(noise, 14)
    grain = ndimage.zoom(grain / grain.std(), 4, order=1)[:height, :width]
    pen, size = recipe.ink, recipe.oversample
    weight = (pen.weight + pen.grain * grain + pen.shade * (1 - np.clip(luma * 1.5, 0, 1))) * size
    weight = np.clip(weight, pen.least * size, pen.most * size)
    ink = 1 - _smooth(weight - 0.8, weight + 0.8, distance)
    out = out * (1 - ink[..., None]) + rgb(pen.colour) * ink[..., None]
    solid = part >= 0
    alpha = np.maximum(solid.astype(float), ink * ndimage.binary_dilation(solid, iterations=4 * size))
    return np.dstack([out, alpha]), part


def split(rgba: np.ndarray, part: np.ndarray, recipe: Recipe) -> tuple[np.ndarray, np.ndarray]:
    """The picture without what goes under, and the same cut to what stands in front of the people. What an under
    part encloses leaves with it, and so does its ink on empty ground: left here they would ride with the body."""
    names, size = recipe.names, recipe.oversample
    solid = part >= 0
    under = ndimage.binary_fill_holes(np.isin(part, [names.index(n) for n in recipe.under]))
    behind = np.isin(part, [names.index(n) for n in recipe.behind])
    back = rgba.copy()
    back[..., 3] *= ~(under | (ndimage.binary_dilation(under, iterations=4 * size) & ~solid))
    near = ndimage.binary_dilation(solid & ~behind & ~under, iterations=2 * size) & ~behind & ~under
    front = back.copy()
    front[..., 3] *= near
    return back, front


def _down(rgba: np.ndarray, size: int) -> np.ndarray:
    height, width = rgba.shape[:2]
    alpha = rgba[..., 3:]

    def blocks(x):
        return x.reshape(height // size, size, width // size, size, -1).mean((1, 3))

    pre, alpha = blocks(rgba[..., :3] * alpha), blocks(alpha)
    return np.dstack([pre / np.maximum(alpha, 1e-4), alpha])


def _bytes(rgba: np.ndarray) -> np.ndarray:
    return (np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8)


def _fitted(meshes: Iterable[Mesh], view: View) -> list[Mesh]:
    """The meshes stretched along x; a normal takes the inverse, or the light would land on the unstretched model."""
    out = []
    for m in meshes:
        facing = m.normals / (view.stretch, 1, 1)
        facing = facing / np.maximum(np.linalg.norm(facing, axis=1, keepdims=True), 1e-9)
        out.append(dataclasses.replace(m, vertices=m.vertices * (view.stretch, 1, 1), normals=facing))
    return out


def _preflight(meshes: Sequence[Mesh], recipe: Recipe) -> None:
    if not meshes:
        raise ProxyError("no meshes to draw")
    for mesh in meshes:
        if not (np.isfinite(mesh.vertices).all() and np.isfinite(mesh.normals).all()):
            raise ProxyError(f"a {mesh.material} mesh has a vertex or a normal that is not a number")
    seen = {m.material for m in meshes}
    unknown = sorted(seen - set(recipe.tones))
    if unknown:
        raise ProxyError(f"meshes of unknown parts: {unknown}; give each one tones in the recipe")
    missing = sorted(recipe.under - seen)
    if missing:
        raise ProxyError(f"no mesh of the under parts {missing}: drop them from the recipe or model them")


def picture(meshes: Sequence[Mesh], view: View, recipe: Recipe, *, engine: Path, cache: Path):
    """The two passes of ``meshes`` from ``view``, stretched, at the recipe's oversample: RGBA floats and parts."""
    _preflight(meshes, recipe)
    fitted = _fitted(meshes, view)

    def rendered(flat: bool) -> np.ndarray:
        return plates.pixels(plates.render(_plate(view, fitted, recipe, flat), engine=engine, cache=cache, fonts=cache))

    return composite(rendered(False), rendered(True), recipe)


def layers(meshes: Sequence[Mesh], view: View, recipe: Recipe, *, engine: Path, cache: Path) -> Layers:
    """The view's plates; ``under`` is drawn whole, with nothing of the rest in front of it."""
    _preflight(meshes, recipe)
    rgba, part = picture(meshes, view, recipe, engine=engine, cache=cache)
    back, front = split(rgba, part, recipe)
    size = recipe.oversample
    under = None
    if recipe.under:
        alone, _ = picture([m for m in meshes if m.material in recipe.under], view, recipe, engine=engine, cache=cache)
        under = _bytes(_down(alone, size))
    return Layers(_bytes(_down(back, size)), _bytes(_down(front, size)), under)
