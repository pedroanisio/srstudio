"""Mae and Bruno in clay: the approved rig's drawing inflated into one surface, the face painted from the rig's own
layers, one pair of arms rigged from the shoulders.

A part is a filled shape of the drawing: the body's coat, the head's coat, each ear's coat. Its volume is the solution
of a Poisson problem on the shape (zero on the outline, a square root of it as the height), so the outline stays
exactly the drawn one and the surface meets it at a right angle: seen from the lens the clay has the card's
silhouette. The body is solved as if mirrored below its base, so it stands on a flat base as wide and deep as the body
is there. Head and body are one surface, the skin, cut into even triangles over both outlines and inflated once over
their joined outline, with a rounder rise where the head is: the head is not a ball standing in front of the chest, so
the chin runs down into the chest with no ledge under it and no collar line. Each point's share of the head (a weight
with no step and no kink) is how far it turns with the head. Coordinates are the drawing's reference pixels, x right
and y down, with z away from the lens: the front of a part is at negative z.

The arms are not drawn into the body. Each is a chain from its shoulder (two rigid bones and a paw) whose paw at rest
lies on the lap where the pose's drawing lays it; a gesture sends the same paw somewhere else, so the arms that rest
are the arms that move and the figure always has one pair of hands. At rest the arm folds into depth as a seated arm
does: the shoulder inside the body's side, the upper arm down the side and the elbow by the hip, the forearm running
down and forward onto the thigh, narrowing from the elbow to the wrist, its clay laid on the belly. Each shoulder's
depth is solved so the arm shows from the front as long as the flat draws it, though the bones keep the reach the Wow
needs. The paw is a flat mitten as wide and tall as the flat's paw, its pad on its face and three toe marks below,
turned to lie along the belly; it lies over its forearm's end, as the flat's paw does, and the ID pass draws arm and
paw in one colour, so the ink runs one outline from the forearm round the paw. Where the room covers one side of the
figure (a :class:`Tuck`: the sofa's arm over Bruno's right side), that side's arm tucks in under the cover: its
shoulder sits just as deep as it takes for none of its upper arm to show beside the cover's edge, so the forearm comes
out from under the cover to the paw, as the flat draws it.

The face is the rig's own: its layers (eyes for the pose and the gaze, the mouth or the viseme heard, the lids of a
blink, the teeth) painted in the drawing's order onto a picture laid flat over the skin's front, and the same layers
given relief in a normal map: the eyes and teeth stand up, ink lines are pressed in like tool marks, an open mouth is a
hollow. Outline inks and painted shade are left out: the clay's own volume and the room's key give both.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import cache

import numpy as np
from PIL import Image, ImageDraw
from scipy import interpolate, ndimage, sparse
from scipy.sparse.linalg import spsolve
from scipy.spatial import Delaunay
from shapely import contains_xy
from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import box as rectangle
from shapely.ops import unary_union

from srstudio import clay
from srstudio.toon_cast import _arms, _eye, _lids, _mouth, _teeth, _viseme
from srstudio.toon_head import _PUPIL_FREE, GAZES, _gazing

Layer = tuple[Sequence[float], str]

OUTLINE_POINTS = 200  # an ink layer of more points than this is an outline the clay's volume replaces
TEXELS = 3  # texture pixels per reference pixel
RINGS, SPOKES = 44, 240  # the grid of a part: rings out from its middle, spokes round it
LIPS = "#a44b4b"  # toon_cast's mouth interior
VISEMES = ("open", "round", "teeth")
NO_TEETH = ("none", "grimace", "kiss", "scream")  # toon_head draws the teeth on every other pose mouth
RELIEF = {"white": 2.2, "ink": -0.9, LIPS: -3.5}  # reference pixels each painted kind stands up from the surface
STROKE_DIM = 0.72  # a fur stroke painted into the clay: the coat darkened, not inked


class FigureError(ValueError):
    """The rig's drawing cannot be built as clay: a layer of a kind it has no rule for, a part that is not there."""


def flatten(shape: Sequence[float], steps: int = 8) -> np.ndarray:
    """A brush shape (start x, y, then cubic segments of six numbers) as the polygon of its outline."""
    if len(shape) < 8 or (len(shape) - 2) % 6:
        raise FigureError(f"a brush shape is a start and cubic segments of six numbers, got {len(shape)} numbers")
    points = [(float(shape[0]), float(shape[1]))]
    x0, y0 = points[0]
    for i in range(2, len(shape), 6):
        c1x, c1y, c2x, c2y, x, y = (float(v) for v in shape[i : i + 6])
        for t in np.linspace(0.0, 1.0, steps + 1)[1:]:
            u = 1.0 - t
            points.append(
                (
                    u**3 * x0 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t**3 * x,
                    u**3 * y0 + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t**3 * y,
                )
            )
        x0, y0 = x, y
    return np.array(points)


@dataclass(frozen=True)
class Box:
    """A rectangle of the drawing, in reference pixels: what one picture covers."""

    x0: float
    y0: float
    x1: float
    y1: float

    def size(self, per: float) -> tuple[int, int]:
        return int(round((self.x1 - self.x0) * per)), int(round((self.y1 - self.y0) * per))

    def uv(self, points: np.ndarray) -> np.ndarray:
        """Texture coordinates of reference ``points``: u to the right, v up from the box's bottom row (OBJ's way)."""
        return np.stack(
            ((points[:, 0] - self.x0) / (self.x1 - self.x0), (self.y1 - points[:, 1]) / (self.y1 - self.y0)), 1
        )


def paint(layers: Sequence[Layer], box: Box, ground: str, ink: str, white: str, per: float = TEXELS) -> np.ndarray:
    """``layers`` filled in order over ``ground``, ``box`` at ``per`` pixels to the reference pixel: RGBA8."""
    over = 3
    width, height = box.size(per)
    picture = Image.new("RGBA", (width * over, height * over), ground)
    pen = ImageDraw.Draw(picture)
    for shape, colour in layers:
        fill = {"ink": ink, "white": white}.get(colour, colour)
        if not (isinstance(fill, str) and fill.startswith("#") and len(fill) == 7):
            raise FigureError(f"a layer's colour is ink, white or #rrggbb, got {colour!r}")
        points = (flatten(shape) - (box.x0, box.y0)) * per * over
        pen.polygon([tuple(p) for p in points.tolist()], fill=fill)
    return np.asarray(picture.resize((width, height), Image.Resampling.LANCZOS), dtype=np.uint8).copy()


def lifts(layers: Sequence[Layer]) -> list[tuple[Sequence[float], float]]:
    """Each painted layer with the relief its kind of paint gives it (:data:`RELIEF`; any other colour lies flat)."""
    return [(shape, RELIEF.get(colour, 0.0)) for shape, colour in layers]


def relief(layers: Sequence[tuple[Sequence[float], float]], box: Box, per: float = TEXELS) -> np.ndarray:
    """The height ``(shape, reference pixels)`` layers give a surface, a later layer over an earlier one as in the
    drawing, softened as a thumb leaves it."""
    over = 2
    width, height = box.size(per)
    field = np.zeros((height * over, width * over))
    for shape, lift in layers:
        mark = Image.new("L", (width * over, height * over), 0)
        points = (flatten(shape) - (box.x0, box.y0)) * per * over
        ImageDraw.Draw(mark).polygon([tuple(p) for p in points.tolist()], fill=255)
        inside = np.asarray(mark, dtype=float) / 255.0
        field = field * (1.0 - inside) + lift * inside  # a later layer covers an earlier one, as in the drawing
    field = field.reshape(height, over, width, over).mean(axis=(1, 3))
    return ndimage.gaussian_filter(field, sigma=0.9 * per / 2.0)


def normal_map(height: np.ndarray) -> np.ndarray:
    """The RGBA normal map of ``height`` (reference pixels over a picture at :data:`TEXELS`), as clay.normal_tile lays
    it: its central difference spans two texture pixels, 2 / TEXELS reference pixels."""
    return clay.normal_tile(height, TEXELS / 2.0)


# --- the parts of a rig's drawing -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Parts:
    """A rig's drawing sorted into what the clay is made of."""

    head: np.ndarray  # the head's coat, an outline polygon
    head_shape: Sequence[float]  # and as the drawing's brush shape
    ears: tuple[np.ndarray, ...]  # each ear's coat
    ear_layers: tuple[tuple[Layer, ...], ...]  # what is painted on each ear: its coat and its inner colour
    body: np.ndarray  # the body's coat
    body_layers: tuple[Layer, ...]  # what is painted on the body: its belly
    body_strokes: tuple[Sequence[float], ...]  # the fur strokes on the body, pressed in
    head_strokes: tuple[Sequence[float], ...]  # and on the head
    coat: str
    shade: str


def _largest(layers: Sequence[Layer], colour: str) -> int:
    hits = [i for i, (shape, c) in enumerate(layers) if c == colour]
    if not hits:
        raise FigureError(f"no layer in the coat {colour}")
    return max(hits, key=lambda i: Polygon(flatten(layers[i][0])).area)


def _inside(shape: Sequence[float], outline: np.ndarray) -> bool:
    return Polygon(outline).buffer(1.0).contains(Polygon(flatten(shape)).buffer(-0.01))


def _dim(colour: str, by: float) -> str:
    rgb = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(round(v * by)):02x}" for v in rgb)


def parts_of(rig) -> Parts:
    """The parts of ``rig``'s drawing: outlines left to the volume, the painted shade left to the light, fur strokes
    kept as pressed marks, an ear's inner colour kept on its ear."""
    coat = rig.look.coat
    skull, trunk = list(rig.skull()), list(rig.trunk())
    head_index = _largest(skull, coat)
    head = flatten(skull[head_index][0])
    ear_indices = [i for i, (_, c) in enumerate(skull) if c == coat and i != head_index]
    if not ear_indices:
        raise FigureError(f"{rig.look.name}: no ear in the drawing")
    ears = tuple(flatten(skull[i][0]) for i in ear_indices)
    ear_layers: list[list[Layer]] = [[skull[i]] for i in ear_indices]
    head_strokes: list[Sequence[float]] = []
    shades: set[str] = set()
    for i, (shape, colour) in enumerate(skull):
        if i == head_index or i in ear_indices:
            continue
        if colour == "ink":
            if len(shape) <= OUTLINE_POINTS:
                head_strokes.append(shape)
            continue
        home = [k for k, ear in enumerate(ears) if _inside(shape, ear)]
        if home:
            ear_layers[home[0]].append((shape, colour))
        else:
            shades.add(colour)  # a coloured layer on the head that is no ear's: the drawing's shadow side
    if len(shades) != 1:
        raise FigureError(f"{rig.look.name}: expected one painted shade on the head, found {sorted(shades)}")
    shade = shades.pop()
    body_index = _largest(trunk, coat)
    body_layers: list[Layer] = []
    body_strokes: list[Sequence[float]] = []
    for i, (shape, colour) in enumerate(trunk):
        if i == body_index or colour == shade:
            continue
        if colour == "ink":
            if len(shape) <= OUTLINE_POINTS:
                body_strokes.append(shape)
            continue
        body_layers.append((shape, colour))
    return Parts(
        head=head,
        head_shape=skull[head_index][0],
        ears=ears,
        ear_layers=tuple(tuple(e) for e in ear_layers),
        body=flatten(trunk[body_index][0]),
        body_layers=tuple(body_layers),
        body_strokes=tuple(body_strokes),
        head_strokes=tuple(head_strokes),
        coat=coat,
        shade=shade,
    )


# --- faces ----------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class Face:
    """What a face shows at one instant: the pose's eyes, where they look, a blink, and the mouth: the pose's own
    mouth, or the viseme heard."""

    eyes: str
    gaze: str
    blink: bool
    mouth: str
    pose_mouth: str

    def key(self) -> str:
        return f"{self.eyes}-{self.gaze}-{'shut' if self.blink else 'open'}-{self.mouth}-{self.pose_mouth}"


def face_layers(rig, face: Face) -> list[Layer]:
    """The face's layers in the order toon_head draws them: the rig's face, the eyes, the mouth, the lids, the teeth."""
    look = rig.look
    if face.gaze not in GAZES:
        raise FigureError(f"no gaze {face.gaze!r}")
    seen = look if face.eyes in _PUPIL_FREE or face.gaze == "ahead" else _gazing(look, face.gaze)
    layers = list(rig.face())
    layers += _eye(seen, seen.eyes[0], face.eyes, 1.0) + _eye(seen, seen.eyes[1], face.eyes, -1.0)
    if face.mouth in VISEMES:
        layers += _viseme(look, face.mouth)
    elif face.mouth == face.pose_mouth:
        layers += _mouth(look, face.mouth)
    else:
        raise FigureError(f"a mouth is the pose's {face.pose_mouth!r} or a viseme of {VISEMES}, got {face.mouth!r}")
    if face.blink:
        layers += _lids(look)
    if look.teeth and face.pose_mouth not in NO_TEETH:
        layers += _teeth(look)
    return layers


# --- volume ---------------------------------------------------------------------------------------------------------


def _mask(outline: np.ndarray, box: Box, per: float) -> np.ndarray:
    width, height = box.size(per)
    picture = Image.new("L", (width, height), 0)
    ImageDraw.Draw(picture).polygon([tuple(p) for p in ((outline - (box.x0, box.y0)) * per).tolist()], fill=255)
    return np.asarray(picture) >= 128


def swell(inside: np.ndarray) -> np.ndarray:
    """The inflation of a shape: the square root of the Poisson solution on it, 0 on its outline, 1 at its fullest."""
    index = -np.ones(inside.shape, int)
    rows, cols = np.nonzero(inside)
    if len(rows) < 4:
        raise FigureError("a part to inflate needs some inside")
    index[rows, cols] = np.arange(len(rows))
    n = len(rows)
    a_rows, a_cols, a_vals = [np.arange(n)], [np.arange(n)], [np.full(n, 4.0)]
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r, c = rows + dr, cols + dc
        ok = (r >= 0) & (r < inside.shape[0]) & (c >= 0) & (c < inside.shape[1])
        neighbour = np.full(n, -1)
        neighbour[ok] = index[r[ok], c[ok]]
        keep = neighbour >= 0
        a_rows.append(np.arange(n)[keep])
        a_cols.append(neighbour[keep])
        a_vals.append(np.full(int(keep.sum()), -1.0))
    matrix = sparse.csr_matrix((np.concatenate(a_vals), (np.concatenate(a_rows), np.concatenate(a_cols))), (n, n))
    u = spsolve(matrix, np.ones(n))
    field = np.zeros(inside.shape)
    field[rows, cols] = np.sqrt(np.maximum(u, 0.0) / u.max())
    return field


@dataclass(frozen=True)
class Volume:
    """A part as two sheets that meet on its outline: the front one textured, the back one plain coat."""

    front: np.ndarray  # vertices, (n, 3)
    back: np.ndarray
    front_normals: np.ndarray
    back_normals: np.ndarray
    triangles: np.ndarray
    uv: np.ndarray
    box: Box
    depth: tuple[float, float]  # the most the front and the back stand out from the middle plane

    def meshes(self, front: str, back: str) -> tuple[clay.Mesh, clay.Mesh]:
        return (
            clay.Mesh(front, self.front, self.front_normals, self.triangles, self.uv),
            clay.Mesh(back, self.back, self.back_normals, self.triangles[:, ::-1].copy()),
        )


def _rays(outline: np.ndarray, centre: np.ndarray, spokes: int = SPOKES) -> np.ndarray:
    """How far from ``centre`` each spoke meets ``outline``: the first crossing, so a shape that is not star-shaped from
    there is cut along the spoke rather than folded."""
    angles = np.linspace(0.0, math.tau, spokes, endpoint=False)
    a, b = outline, np.roll(outline, -1, axis=0)
    edge = b - a
    reach = np.empty(spokes)
    for k, angle in enumerate(angles):
        d = np.array((math.cos(angle), math.sin(angle)))
        denom = d[0] * edge[:, 1] - d[1] * edge[:, 0]
        rel = a - centre
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (rel[:, 0] * edge[:, 1] - rel[:, 1] * edge[:, 0]) / denom
            s = (rel[:, 0] * d[1] - rel[:, 1] * d[0]) / denom
        hit = (np.abs(denom) > 1e-12) & (t > 1e-6) & (s >= -1e-9) & (s <= 1 + 1e-9)
        if not hit.any():
            raise FigureError("a spoke from the middle of a part meets no outline")
        reach[k] = t[hit].min()
    return reach


def _vertex_normals(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    a, b, c = (points[triangles[:, i]] for i in range(3))
    faces = np.cross(b - a, c - a)
    normals = np.zeros_like(points)
    for i in range(3):
        np.add.at(normals, triangles[:, i], faces)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.where(length > 0, length, 1.0)


def _wound(flat: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """``tris`` all wound one way round in the plane, as most of them are: a sheet whose fan turned the other way
    would show its back at the middle, a hole where the part is deepest."""
    a, b, c = flat[tris[:, 0]], flat[tris[:, 1]], flat[tris[:, 2]]
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    way = np.sign(np.sum(np.sign(area)))
    out = tris.copy()
    wrong = np.sign(area) == -way
    out[wrong] = out[wrong][:, ::-1]
    return out


def _whole(outline: np.ndarray, base: float | None) -> np.ndarray:
    """The shape a part is solved on: its outline, or with ``base`` (a reference y) its outline and its mirror there,
    so the part stands on that line once cut flat on it."""
    shape = Polygon(outline).buffer(0)
    if base is not None:
        mirrored = np.stack((outline[:, 0], 2 * base - outline[:, 1]), 1)
        shape = unary_union([shape, Polygon(mirrored).buffer(0)]).buffer(0.5).buffer(-0.5)
    if shape.geom_type != "Polygon":
        raise FigureError(f"a part is one piece, got {shape.geom_type}")
    return np.array(shape.exterior.coords)[:-1]


def _box(whole: np.ndarray) -> Box:
    x0, y0 = whole.min(0) - 2
    x1, y1 = whole.max(0) + 2
    return Box(float(x0), float(y0), float(x1), float(y1))


def _sample(field: np.ndarray, box: Box, flat: np.ndarray) -> np.ndarray:
    """``field`` (one value per reference pixel of ``box``) at the reference points ``flat``, 0 off the box."""
    return ndimage.map_coordinates(field, [flat[:, 1] - box.y0 - 0.5, flat[:, 0] - box.x0 - 0.5], order=1, cval=0.0)


@dataclass(frozen=True)
class Grid:
    """A shape cut into rings out from its fullest point and spokes round it, the last ring on its outline."""

    flat: np.ndarray  # (n, 2) reference points: the middle, then ring after ring
    triangles: np.ndarray
    direction: np.ndarray  # (spokes, 2): each spoke's way out, the outline's normal there
    box: Box

    @property
    def rim(self) -> np.ndarray:
        return np.arange(len(self.flat) - len(self.direction), len(self.flat))


def _grid(whole: np.ndarray, box: Box, field: np.ndarray, rings: int, spokes: int) -> Grid:
    peak = np.unravel_index(np.argmax(field), field.shape)
    centre = np.array((box.x0 + peak[1] + 0.5, box.y0 + peak[0] + 0.5))
    reach = _rays(whole, centre, spokes)
    rho = 1.0 - (1.0 - np.linspace(0.0, 1.0, rings + 1)[1:]) ** 1.6  # rings close up toward the outline
    angles = np.linspace(0.0, math.tau, spokes, endpoint=False)
    direction = np.stack((np.cos(angles), np.sin(angles)), 1)
    flat = centre + (rho[:, None, None] * reach[None, :, None]) * direction[None, :, :]
    flat = np.concatenate((centre[None, :], flat.reshape(-1, 2)))
    triangles = [(0, 1 + (k + 1) % spokes, 1 + k) for k in range(spokes)]
    triangles += [(1 + t[0], 1 + t[2], 1 + t[1]) for t in clay._sheet(rings, spokes, True)]
    return Grid(flat, _wound(flat, np.array(triangles, int)), direction, box)


def _volume(grid: Grid, zf: np.ndarray, zb: np.ndarray, base: float | None) -> Volume:
    """The two sheets of ``grid`` at the depths ``zf`` and ``zb``, cut flat on ``base`` when it stands on one."""
    xy = grid.flat.copy()
    under = np.zeros(len(xy), bool)
    if base is not None:
        under = xy[:, 1] > base
        xy[under, 1] = base
    tris = grid.triangles
    front_points = np.column_stack((xy, zf))
    back_points = np.column_stack((xy, zb))
    if _vertex_normals(front_points, tris)[0, 2] > 0:  # the middle of the front faces the lens: -z
        tris = tris[:, ::-1].copy()
    nf = _vertex_normals(front_points, tris)
    nb = -_vertex_normals(back_points, tris)
    out = np.column_stack((grid.direction, np.zeros(len(grid.direction))))
    nf[grid.rim], nb[grid.rim] = out, out
    nf[under], nb[under] = (0.0, 1.0, 0.0), (0.0, 1.0, 0.0)
    return Volume(
        front=front_points,
        back=back_points,
        front_normals=nf,
        back_normals=nb,
        triangles=tris,
        uv=grid.box.uv(grid.flat),
        box=grid.box,
        depth=(float(-zf.min()), float(zb.max())),
    )


def inflate(outline: np.ndarray, front: float, back: float, *, base: float | None = None, bump=None) -> Volume:
    """``outline`` as clay, standing ``front`` times its inradius toward the lens and ``back`` away. With ``base`` (a
    reference y) the part is solved as mirrored there and cut flat on it, so it stands on that line. ``bump(x, y)``
    adds reference pixels of relief to the front."""
    whole = _whole(outline, base)
    box = _box(whole)
    inside = _mask(whole, box, 1.0)
    field = swell(inside)
    inradius = float(ndimage.distance_transform_edt(inside).max())
    grid = _grid(whole, box, field, RINGS, SPOKES)
    sample = np.clip(_sample(field, box, grid.flat), 0.0, 1.0)
    sample[grid.rim] = 0.0  # the outline itself: exactly on the drawing's line
    lift = np.zeros(len(grid.flat)) if bump is None else np.asarray(bump(grid.flat[:, 0], grid.flat[:, 1]), float)
    zf = -(front * inradius * sample + lift * np.minimum(sample * 4.0, 1.0))
    zb = back * inradius * sample
    return _volume(grid, zf, zb, base)


# --- head and body as one surface -------------------------------------------------------------------------------------

SPOKES_SKIN = 360  # points round the skin's outline; it is head and body, so it is not star-shaped from any point
SOFT = 8.0  # reference pixels the distances the skin's weights are read from are softened over
SKIN_STEP = 3.0  # reference pixels between the skin's points inside its outline


def _even_grid(whole: np.ndarray, box: Box, rim_points: int, step: float) -> Grid:
    """A shape cut into even triangles: points ``step`` apart inside it, and ``rim_points`` evenly along its outline,
    last and in its order. A head on a body is no star from any middle, so it is not cut into spokes from one."""
    shape = Polygon(whole)
    ring = shape.exterior
    along = np.linspace(0.0, ring.length, rim_points, endpoint=False)
    rim = np.array([ring.interpolate(d).coords[0] for d in along])
    ahead = np.array([ring.interpolate((d + 0.5) % ring.length).coords[0] for d in along])
    behind = np.array([ring.interpolate((d - 0.5) % ring.length).coords[0] for d in along])
    tangent = ahead - behind
    direction = np.stack((tangent[:, 1], -tangent[:, 0]), 1)
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    if contains_xy(shape, *(rim + direction * 1.0).T).mean() > 0.5:  # pointing in: the outline runs the other way
        direction = -direction
    xs = np.arange(box.x0 + step / 2.0, box.x1, step)
    ys = np.arange(box.y0 + step / 2.0, box.y1, step)
    gx, gy = np.meshgrid(xs, ys)
    inner = np.column_stack((gx.ravel(), gy.ravel()))
    inner = inner[contains_xy(shape.buffer(-step * 0.45), inner[:, 0], inner[:, 1])]
    flat = np.concatenate((inner, rim))
    tris = Delaunay(flat).simplices
    middle = flat[tris].mean(axis=1)
    tris = tris[contains_xy(shape, middle[:, 0], middle[:, 1])]  # the hull's triangles over a notch are not the shape
    used = np.zeros(len(flat), bool)
    used[tris.ravel()] = True
    if not used[len(inner) :].all():
        raise FigureError("a point of the skin's outline is on no triangle")
    renumber = np.cumsum(used) - 1
    flat, tris = flat[used], renumber[tris]
    return Grid(flat, _wound(flat, tris), direction, box)


BLEND = 48.0  # reference pixels in from the head's outline over which the surface turns from the body's to the head's


def smoothstep(x: np.ndarray) -> np.ndarray:
    """0 to 1 over ``x`` from 0 to 1, flat at both ends: a weight with no step and no kink."""
    t = np.clip(x, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


SKIN_DEPTH = (0.55, 0.45)  # front and back, times the skin's inradius: head and body inflated as one shape
HEAD_ROUND = (0.3, 0.15)  # front and back, times the head's inradius: how much rounder than the shape the head is
HEAD_RISE = 1.2  # head inradii in from the head's outline over which its roundness rises from nothing


def skin(head: np.ndarray, body: np.ndarray, base: float, bump=None) -> tuple[Volume, np.ndarray]:
    """The head's outline and the body's as one clay surface, and each point's share of the head (its weight when the
    head turns). The two outlines are inflated as one shape, as :func:`inflate` would inflate it, so the chin runs on
    into the chest as the drawing's one silhouette does: no ledge under it for the light to leave dark, no line. The
    head is rounder than that by a relief of :data:`HEAD_ROUND` that rises from its outline with no slope over
    :data:`HEAD_RISE`, so it neither steps nor creases where it lies on the body. ``bump`` is the face's relief."""
    head_whole, body_whole = _whole(head, None), _whole(body, base)
    union = unary_union([Polygon(head_whole), Polygon(body_whole)]).buffer(1.0).buffer(-1.0)
    if union.geom_type != "Polygon":
        raise FigureError(f"the head and the body do not meet: {union.geom_type}")
    whole = np.array(union.exterior.coords)[:-1]
    box = _box(whole)
    grid = _even_grid(whole, box, SPOKES_SKIN, SKIN_STEP)
    shape = _mask(whole, box, 1.0)
    fullness = np.clip(_sample(swell(shape), box, grid.flat), 0.0, 1.0)
    radius = float(ndimage.distance_transform_edt(shape).max())

    def part(outline: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        inside = _mask(outline, box, 1.0)
        own = np.clip(_sample(swell(inside), box, grid.flat), 0.0, 1.0)
        # how far inside it and how far outside, softened: a distance creases where two parts of an outline are as
        # near, along a corner's bisector, and a weight or a relief read from it would crease there too
        within = _sample(ndimage.gaussian_filter(ndimage.distance_transform_edt(inside), SOFT), box, grid.flat)
        without = _sample(ndimage.gaussian_filter(ndimage.distance_transform_edt(~inside), SOFT), box, grid.flat)
        return own, within, without, float(ndimage.distance_transform_edt(inside).max())

    sh, wh, oh, rh = part(head_whole)
    _, wb, _, _ = part(body_whole)
    # the head's share: all of it outside the body, rising from its outline into it over BLEND where it lies on the
    # body, and where the two outlines meet, shared along the outline between them
    weight = 1.0 - (1.0 - smoothstep(wh / BLEND)) * smoothstep(wb / BLEND)
    weight *= 1.0 - smoothstep(oh / BLEND)
    lift = np.zeros(len(grid.flat)) if bump is None else np.asarray(bump(grid.flat[:, 0], grid.flat[:, 1]), float)
    round_ = rh * smoothstep(wh / (HEAD_RISE * rh))
    zf = -(SKIN_DEPTH[0] * radius * fullness + HEAD_ROUND[0] * round_ + lift * np.minimum(sh * 4.0, 1.0))
    zb = SKIN_DEPTH[1] * radius * fullness + HEAD_ROUND[1] * round_
    zf[grid.rim] = zb[grid.rim] = 0.0  # the outline itself: front and back meet on the drawing's line
    return _volume(grid, zf, zb, base), weight


def front_of(volume: Volume):
    """The depth of ``volume``'s front at any point of the drawing: linear inside it, the nearest outside. A base cut
    flat is left out, its points stacked on one line."""
    keep = np.zeros(len(volume.front), bool)
    keep[np.unique(volume.front[:, :2], axis=0, return_index=True)[1]] = True  # the first point at each place only
    xy, z = volume.front[keep, :2], volume.front[keep, 2]
    inside = interpolate.LinearNDInterpolator(xy, z)
    nearest = interpolate.NearestNDInterpolator(xy, z)

    def depth(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        out = np.asarray(inside(x, y), float)
        missing = np.isnan(out)
        if missing.any():
            out[missing] = nearest(x[missing], y[missing])
        return out

    return depth


# --- the figure -------------------------------------------------------------------------------------------------------

HEAD_DEPTH = (0.78, 0.62)  # front and back, times the part's inradius: a round head
BODY_DEPTH = (0.55, 0.45)
EAR_DEPTH = {"bear": (0.42, 0.42), "rabbit": (0.24, 0.24)}
MUZZLE, NOSE = 9.0, 7.0  # reference pixels the bear's muzzle and either nose stand off the head
BASE = 832.0  # the bust's lowest drawn row: the sofa room shows it whole, its base on the cushion


# --- the arms ---------------------------------------------------------------------------------------------------------

UPPER, FORE = 92.0, 96.0  # reference pixels from the shoulder to the elbow and on to the wrist: the Wow's full reach
WRIST = 0.6  # the wrist's radius over the elbow's: the forearm narrows from the elbow (the flat arm's) to the wrist
ELBOW_AT = 8  # the elbow's index on an arm's middle line (:func:`arm_line`): the upper arm before it, the forearm after
PAW_TILT = 20.0  # degrees the paw turns about the level: its toes toward the lens, its top away
PAW_FOLLOW = 10.0  # reference pixels either side of the paw's middle over which the belly's slope across is read
PAW_FLAT = 0.5  # the paw's depth over its seen height: a mitten, flat front to back
PAW_SINK = 0.3  # how far into the paw, over the paw's radius that way, the wrist goes
TOES = (-0.45, 0.0, 0.45)  # the three toe marks across the paw's lower front, over its half width
PRESS = 0.25  # the share of the laid forearm's radius pressed into the belly
COVER = 1.0  # reference pixels the paw's middle stands in front of its forearm's end, which runs in under it
SIDES = ("left", "right")  # in the drawing, before any mirror
# A seated arm at rest: the upper arm hangs down the side inside the body, the forearm runs down and forward onto the
# thigh, so from the front it shows short although its bones are long. Both shoulders sit on one row, SHOULDER_UP
# above the flat arms' tops on average, each SHOULDER_IN in from the body's side on that row; the elbow bends toward
# POLE. Each shoulder's depth is solved within SHOULDER_BACK (behind the skin's middle plane; negative: in front of
# it) so its arm shows as long as its own flat arm: the flat draws its two arms unlike, so no one depth fits both. The
# deeper the shoulder, the more of the upper arm the body hides, while the forearm's fall barely moves. Searched: over
# that range each arm shows in one piece, its forearm falling at least 30 degrees.
SHOULDER_IN = 22.0
SHOULDER_UP = 82.0
SHOULDER_BACK = (-35.0, -5.0)  # the nearest and the farthest the shoulder's depth is solved in
FIT_TOLERANCE = 1.0  # reference pixels the solved arm may show off the flat's length: two SHOWN_STEPs
SHOWN_STEP = 0.5  # reference pixels between the points an arm's shown length is measured at
FIT_STEPS = 40  # bisections at the most: the solve ends whatever the arm shows
POLE = (1.0, 1.0, 0.8)  # out (x by the side), down and back: the elbow at the side, by the hip
ARM_SAMPLES = 25  # points along an arm's middle line, shoulder to wrist
TUCK_STEP = 0.5  # reference pixels of depth a tucked shoulder is set back by at a time
TUCK_RING = 48  # points round each ring of the upper arm that a tuck looks at


@dataclass(frozen=True)
class Tuck:
    """Where the room covers one side of a figure at rest: on ``side`` (in the drawing, before any mirror) everything
    outward of ``edge`` (reference pixels: past it on the right side, short of it on the left) lies under the room's
    drawn front, as the sofa's arm lies over Bruno's right side. That side's arm tucks in under it."""

    side: str
    edge: float

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise FigureError(f"a tuck on no side the figure has: {self.side!r}")

    def beside(self, x: np.ndarray) -> np.ndarray:
        """Where ``x`` lies beside the cover, on the open side of its edge."""
        return x < self.edge if self.side == "right" else x > self.edge


@dataclass(frozen=True)
class ArmChain:
    """One arm, rigged from its shoulder: two bones and a paw. The paw at ``rest`` lies on the lap where the pose's
    drawing lays it; every gesture is that same paw sent somewhere else (:func:`reach`)."""

    side: str
    shoulder: np.ndarray  # (3,) reference pixels, its depth solved so the arm shows the flat's length (_fitted)
    upper: float
    fore: float
    radii: tuple[float, float]  # at the elbow (the whole upper arm too) and at the wrist
    paw_size: tuple[float, float, float]  # the paw's own radii, across, tall and deep, before its turn
    paw_turn: np.ndarray  # (3, 3) the paw's turn (:func:`_turn`): tilted toes to the lens, its back along the belly
    pad: str  # the paw's pad colour, the drawing's own
    rest: np.ndarray  # (3,) the middle of the paw at rest
    pole: np.ndarray  # (3,) unit: the way the elbow bends
    lap: Polygon | None = None  # where the forearm's clay lies over the skin rather than through it: the outline below
    skin: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None  # the skin's front depth there


@dataclass(frozen=True)
class Joints:
    """Where an arm's joints are, reference pixels: the paw's middle past the wrist, along the forearm."""

    shoulder: np.ndarray
    elbow: np.ndarray
    wrist: np.ndarray
    paw: np.ndarray


def _two_bones(start: np.ndarray, end: np.ndarray, a: float, b: float, pole: np.ndarray) -> tuple[np.ndarray, ...]:
    """The elbow and the wrist of bones ``a`` and ``b`` from ``start`` toward ``end``: the wrist as near ``end`` as the
    bones reach, the elbow bent toward ``pole``."""
    way = end - start
    far = float(np.linalg.norm(way))
    if far < 1e-9:
        raise FigureError("an arm cannot reach its own shoulder")
    u = way / far
    d = min(max(far, abs(a - b) + 1e-3), (a + b) * 0.999)
    bend = math.acos(max(-1.0, min(1.0, (a * a + d * d - b * b) / (2.0 * a * d))))
    v = pole - (pole @ u) * u
    if np.linalg.norm(v) < 1e-9:
        v = np.cross(u, (0.0, 0.0, 1.0))
    v = v / np.linalg.norm(v)
    elbow = start + a * (math.cos(bend) * u + math.sin(bend) * v)
    wrist = start + d * u
    return elbow, wrist


def reach(chain: ArmChain, target: np.ndarray) -> Joints:
    """``chain`` with its paw's middle sent to ``target`` (reference pixels), or as far toward it as the bones go."""
    target = np.asarray(target, float)
    forearm = (target - chain.shoulder) / max(float(np.linalg.norm(target - chain.shoulder)), 1e-9)
    wrist_at = target - _into(chain, forearm)
    for _ in range(6):  # the wrist goes into the paw the way the forearm comes, which turns with the elbow: settle both
        elbow, wrist = _two_bones(chain.shoulder, wrist_at, chain.upper, chain.fore, chain.pole)
        forearm = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        wrist_at = target - _into(chain, forearm)
    elbow, wrist = _two_bones(chain.shoulder, wrist_at, chain.upper, chain.fore, chain.pole)
    forearm = (wrist - elbow) / np.linalg.norm(wrist - elbow)
    return Joints(chain.shoulder.copy(), elbow, wrist, wrist + _into(chain, forearm))


def _into(chain: ArmChain, way: np.ndarray) -> np.ndarray:
    """From the wrist to the paw's middle, for a forearm running ``way``: on the drawing's plane, :data:`PAW_SINK` of
    the paw's seen radius that way, so the forearm runs in under the mitten; in depth, the paw's middle in front of
    the wrist by the wrist's radius and :data:`COVER`, so the forearm's end lies behind the paw's middle and the paw
    covers it, as the flat draws its arm going in behind the paw."""
    flat = float(np.hypot(way[0], way[1]))
    step = (way[0] / flat, way[1] / flat) if flat > 1e-9 else (0.0, 0.0)
    along = _along(chain, way)
    return np.array((along * step[0], along * step[1], -(chain.radii[1] + COVER)))


def _along(chain: ArmChain, way: np.ndarray) -> float:
    """How far past the wrist the paw's middle lies on the drawing's plane, along ``way``: :data:`PAW_SINK` of the
    paw's seen radius that way."""
    rx, ry, rz = _half(chain.paw_size, chain.paw_turn)
    flat = np.hypot(way[0], way[1])
    if flat < 1e-9:
        return PAW_SINK * rz
    dx, dy = way[0] / flat, way[1] / flat
    return PAW_SINK / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)


def _tilt() -> np.ndarray:
    """The paw's turn about the level, as a matrix: its bottom toward the lens (-z), its top away."""
    t = math.radians(PAW_TILT)
    return np.array(((1.0, 0.0, 0.0), (0.0, math.cos(t), math.sin(t)), (0.0, -math.sin(t), math.cos(t))))


def _turn(slope: float) -> np.ndarray:
    """The paw's turn as a matrix: tilted about the level (:func:`_tilt`), then turned about the upright so that its
    back runs along a belly whose depth changes by ``slope`` per reference pixel across."""
    a = math.atan(slope)
    c, s = math.cos(a), math.sin(a)
    return np.array(((c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c))) @ _tilt()


def _half(size: Sequence[float], turn: np.ndarray) -> np.ndarray:
    """An ellipsoid of radii ``size`` turned by ``turn``: its half extent across, tall and deep."""
    return np.sqrt(((turn * np.asarray(size, float)) ** 2).sum(axis=1))


def _paw_size(turn: np.ndarray, across: float, tall: float, deep: float) -> tuple[float, float, float]:
    """The radii of a paw ``deep`` through its own thickness that, turned by ``turn``, the lens sees ``across`` and
    ``tall`` (half extents): the two squared radii solve two linear equations."""
    m = turn**2
    a = np.array(((m[0, 0], m[0, 1]), (m[1, 0], m[1, 1])))
    b = np.array((across**2 - m[0, 2] * deep**2, tall**2 - m[1, 2] * deep**2))
    squared = np.linalg.solve(a, b)
    if np.any(squared <= 0.0):
        raise FigureError(f"no paw {deep:.1f} deep shows {across:.1f} by {tall:.1f} turned so")
    return float(math.sqrt(squared[0])), float(math.sqrt(squared[1])), deep


def _clear(surface: Callable[[np.ndarray, np.ndarray], np.ndarray], x: float, y: float, size: Sequence[float],
           turn: np.ndarray, wrist: float) -> float:  # fmt: skip
    """The depth of a paw's middle at (``x``, ``y``) on the lap: as far back as it goes with every point of its side
    that faces the lens in front of the skin, so the belly cuts nothing out of it, and its middle :data:`COVER` in
    front of its forearm's end laid on the belly anywhere under it (a forearm ``wrist`` in radius there), so it lies
    over that end as the flat's paw does."""
    rows, cols = 49, 96
    polar = np.linspace(0.0, math.pi, rows)[:, None]
    around = np.linspace(0.0, math.tau, cols, endpoint=False)[None, :]
    unit = np.stack(
        (np.sin(polar) * np.cos(around), -np.cos(polar) * np.ones_like(around), np.sin(polar) * np.sin(around)), axis=2
    ).reshape(-1, 3)
    radii = np.asarray(size, float)
    points = (unit * radii) @ turn.T
    normals = (unit / radii) @ turn.T
    facing = normals[:, 2] < 0.0
    p = points[facing]
    skin = surface(x + p[:, 0], y + p[:, 1])
    laid = float(skin.min()) - (1.0 - PRESS) * wrist  # the laid forearm's middle where the belly comes nearest
    return min(float((skin - p[:, 2]).min()), laid - wrist - COVER)


def paw_depth(chain: ArmChain) -> float:
    """How far the turned paw stands in front of and behind its middle."""
    return float(_half(chain.paw_size, chain.paw_turn)[2])


def toe_columns(chain: ArmChain) -> tuple[float, ...]:
    """The toe marks' columns across the paw, from its middle (reference pixels)."""
    return tuple(k * chain.paw_size[0] for k in TOES)


def _ellipsoid(model: clay.Model, material: str, centre: np.ndarray, size: Sequence[float], turn: np.ndarray) -> None:
    """An ellipsoid of radii ``size`` turned by ``turn`` about its middle, laid at ``centre``."""
    rows, cols = 25, 48
    polar = np.linspace(0.0, math.pi, rows)[:, None]
    around = np.linspace(0.0, math.tau, cols, endpoint=False)[None, :]
    unit = np.stack(
        (np.sin(polar) * np.cos(around), -np.cos(polar) * np.ones_like(around), np.sin(polar) * np.sin(around)), axis=2
    ).reshape(-1, 3)
    radii = np.asarray(size, float)
    normals = unit / radii
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    tris = []
    for i in range(rows - 1):
        for j in range(cols):
            a, b = i * cols + j, i * cols + (j + 1) % cols
            tris += [(a, b, b + cols), (a, b + cols, a + cols)]
    model.surface(material, (unit * radii) @ turn.T + centre, normals @ turn.T, tris)


def arm_meshes(chain: ArmChain, joints: Joints, coat: str, pad: str) -> dict[str, tuple[clay.Mesh, ...]]:
    """The clay of an arm at ``joints``: the upper arm a roll as wide as the elbow, the forearm narrowing to the wrist,
    which runs into the paw; the paw a flat mitten as wide and tall as the flat's paw, tilted toes toward the lens, its
    pad on its front and three toe marks below it, in the reel's ink. Keyed arm, paw and pad (the pad's part holds the
    toes, material ``coat`` with ``-arm`` turned to ``-toe``); materials ``coat`` and ``pad``."""
    path, radii = arm_line(chain, joints)
    arm = clay.Model()
    arm.ribbon(coat, path, radii.tolist(), sides=20)
    arm.ell(coat, tuple(joints.shoulder), (chain.radii[0],) * 3)
    rx, ry, rz = chain.paw_size
    turn = chain.paw_turn
    paw = clay.Model()
    _ellipsoid(paw, coat, joints.paw, (rx, ry, rz), turn)
    on = clay.Model()
    face = -rz * math.sqrt(max(0.0, 1.0 - 0.1**2)) * 0.8
    _ellipsoid(on, pad, joints.paw + turn @ (0.0, -0.1 * ry, face), (rx * 0.42, ry * 0.36, rz * 0.3), turn)
    toe = coat.rsplit("-", 1)[0] + "-toe"
    for column in toe_columns(chain):
        y = 0.58 * ry
        depth = -rz * math.sqrt(max(0.0, 1.0 - (column / rx) ** 2 - 0.58**2)) * 0.9
        _ellipsoid(on, toe, joints.paw + turn @ (column, y, depth), (rx * 0.06, ry * 0.2, rz * 0.22), turn)
    return {"arm": arm.meshes(), "paw": paw.meshes(), "pad": on.meshes()}


def _paws(rig) -> dict[str, tuple[np.ndarray, str]]:
    """Each paw of the pose's own drawing at rest (``desk``): its box's corners and its pad's colour, by side."""

    under, _ = _arms(rig.look, "desk", 0)
    coat = rig.look.coat
    fills = [(flatten(shape), i) for i, (shape, colour) in enumerate(under) if colour == coat]
    found: dict[str, tuple[np.ndarray, str]] = {}
    for side in SIDES:
        mine = [(outline, i) for outline, i in fills if (outline[:, 0].mean() < CENTRE) == (side == "left")]
        if len(mine) != 2:
            raise FigureError(f"{rig.look.name}: the desk pose draws an arm and a paw on each side, got {len(mine)}")
        outline, i = min(mine, key=lambda row: Polygon(row[0]).area)  # the paw is the smaller fill
        pads = [c for shape, c in under[i + 1 :] if c not in ("ink", coat)]
        if not pads:
            raise FigureError(f"{rig.look.name}: the {side} paw has no pad")
        found[side] = (np.array([outline.min(0), outline.max(0)]), pads[0])
    return found


CENTRE = 185.0  # toon_cast.CENTRE: the drawing's middle column


@dataclass(frozen=True)
class FlatArm:
    """The flat's arm at rest, as toon_torso draws it (reference pixels): its middle line from where it leaves the body
    to the wrist, its paw's middle, its full width at the wrist, and the line's length."""

    path: tuple[tuple[float, float], ...]
    paw: tuple[float, float]
    width: float

    @property
    def length(self) -> float:
        return float(sum(math.dist(a, b) for a, b in zip(self.path, self.path[1:], strict=False)))


class _Recorded:
    """A look's drawing that writes down the arms asked of it: the points and the paw of each limb, in order."""

    def __init__(self, drawing) -> None:
        self.drawing = drawing
        self.limbs: list[tuple[Sequence[tuple[float, float]], tuple[float, float]]] = []

    def limb(self, points, look, paw, toes):
        self.limbs.append((points, paw))
        return self.drawing.limb(points, look, paw, toes)

    def __getattr__(self, name: str):
        return getattr(self.drawing, name)


def flat_rest_arms(rig) -> dict[str, FlatArm]:
    """The flat's two arms in the resting pose (``desk``), read off the drawing itself: the pose's arm points as
    toon_cast hands them to the look, laid inside the body by its torso as the flat card draws them."""
    from srstudio.toon_torso import PAW

    drawing = rig.look.drawing
    torso = getattr(drawing, "torso", None)
    if torso is None:
        raise FigureError(f"{rig.look.name}: the clay reads its arms off a torso-drawn look")
    recorder = _Recorded(drawing)
    _arms(replace(rig.look, drawing=recorder), "desk", 0)
    if len(recorder.limbs) != 2:
        raise FigureError(f"{rig.look.name}: the resting pose draws {len(recorder.limbs)} arms, not a pair")
    out: dict[str, FlatArm] = {}
    for points, paw in recorder.limbs:
        side = "left" if points[0][0] < CENTRE else "right"
        path = tuple((float(x), float(y)) for x, y in torso.arm_path(points))
        at = torso.keep(paw, torso.arm * PAW)
        out[side] = FlatArm(path, (float(at[0]), float(at[1])), float(torso.arm))
    if sorted(out) != list(SIDES):
        raise FigureError(f"{rig.look.name}: the resting arms are not one on each side: {sorted(out)}")
    return out


def _chains(rig, surface, body: np.ndarray) -> tuple[ArmChain, ArmChain]:
    """The two arms: both shoulders on one row above where the flat's arms leave the body, each in from the body's
    side; the elbow as wide as the flat's arm and the wrist narrower; the paw a mitten covering the flat paw's box,
    laid where the flat lays it on the thigh."""
    flat = flat_rest_arms(rig)
    outline = Polygon(body)
    level = sum(flat[k].path[0][1] for k in SIDES) / len(SIDES)  # one body, both shoulders on one row
    out: list[ArmChain] = []
    for side, (corners, pad) in zip(SIDES, (_paws(rig)[k] for k in SIDES), strict=True):
        arm = flat[side]
        r0 = arm.width / 2.0
        r1 = WRIST * r0
        top_x = arm.path[0][0]
        sy = level - SHOULDER_UP
        row = LineString([(top_x - 400.0, sy), (top_x + 400.0, sy)]).intersection(outline)
        if row.is_empty:
            raise FigureError(f"{rig.look.name}: no body at the {side} shoulder's row")
        edge = row.bounds[0] if side == "left" else row.bounds[2]
        sx = edge + SHOULDER_IN if side == "left" else edge - SHOULDER_IN
        shoulder = np.array((sx, sy, sum(SHOULDER_BACK) / 2.0))  # its depth solved by :func:`_fitted`
        if not outline.buffer(-r0).contains(ShapelyPoint(sx, sy)):
            raise FigureError(f"{rig.look.name}: the {side} shoulder at ({sx:.0f}, {sy:.0f}) is not inside the body")
        (x0, y0), (x1, y1) = corners
        across, tall = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        px, py = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        side_depths = surface(np.array((px - PAW_FOLLOW, px + PAW_FOLLOW)), np.array((py, py)))
        turn = _turn(float(side_depths[1] - side_depths[0]) / (2.0 * PAW_FOLLOW))
        size = _paw_size(turn, across, tall, PAW_FLAT * tall)  # the lens sees the flat paw's box
        rest = np.array((px, py, _clear(surface, px, py, size, turn, r1)))
        pole = np.array((POLE[0] * (-1.0 if side == "left" else 1.0), POLE[1], POLE[2]))
        below = rectangle(-1e4, shoulder[1], 1e4, 1e4)  # below the shoulder: a raised arm is never laid
        lap = outline.intersection(below)
        out.append(ArmChain(side, shoulder, UPPER, FORE, (r0, r1), size, turn, pad, rest,
                            pole / np.linalg.norm(pole), lap, surface))  # fmt: skip
    return out[0], out[1]


def arm_line(chain: ArmChain, joints: Joints) -> tuple[np.ndarray, np.ndarray]:
    """An arm's middle line from the shoulder through the elbow (rounded) to the wrist, and its radius at each point.
    Where the forearm's bone passes under the skin on the lap (``chain.lap``) its clay lies on the skin instead,
    pressed in by :data:`PRESS` of its radius, as soft clay rests on a round belly: the bones keep their length, only
    the roll over them bends."""
    path = np.concatenate(
        (np.linspace(joints.shoulder, joints.elbow, 9), np.linspace(joints.elbow, joints.wrist, 9)[1:])
    )
    for _ in range(3):  # round the elbow: each inner point toward its neighbours' middle
        path[1:-1] = 0.5 * path[1:-1] + 0.25 * (path[:-2] + path[2:])
    run = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))))
    share = np.clip((run - run[ELBOW_AT]) / max(run[-1] - run[ELBOW_AT], 1e-9), 0.0, 1.0)
    radii = chain.radii[0] + (chain.radii[1] - chain.radii[0]) * share  # the upper arm the elbow's width throughout
    if chain.lap is not None and chain.skin is not None:
        fore = np.arange(len(path)) >= 8  # from the elbow on
        on = fore & contains_xy(chain.lap, path[:, 0], path[:, 1])
        if on.any():
            rests = chain.skin(path[on, 0], path[on, 1]) - radii[on] * (1.0 - PRESS)
            for _ in range(4):  # rolled out of the body at the elbow, not stepped: eased, never below the skin
                path[on, 2] = np.minimum(path[on, 2], rests)
                path[1:-1, 2] = 0.5 * path[1:-1, 2] + 0.25 * (path[:-2, 2] + path[2:, 2])
            path[on, 2] = np.minimum(path[on, 2], rests)
    return path, radii


def arm_shown(fig: Figure, chain: ArmChain, joints: Joints) -> float:
    """How long ``chain`` at ``joints`` shows from the front, reference pixels: its middle line's length on the
    drawing's plane wherever the arm is seen, outside the figure's outline or with its near side in front of the
    skin's front. Every piece counts: an arm that shows twice, a stub at the shoulder and a forearm, shows both."""
    return float(sum(arm_pieces(fig, chain, joints)))


def arm_start(fig: Figure, chain: ArmChain, joints: Joints) -> np.ndarray:
    """Where ``chain`` at ``joints`` first shows from the front, on its middle line (reference pixels, x and y)."""
    line, shown = _shown(fig, chain, joints)
    if not shown.any():
        raise FigureError(f"the {chain.side} arm does not show at all")
    return line[int(np.argmax(shown)), :2]


def _shown(fig: Figure, chain: ArmChain, joints: Joints) -> tuple[np.ndarray, np.ndarray]:
    """``chain``'s middle line, densely, and whether each of its points shows from the front."""
    return _shown_on(_rim(fig.skin), front_of(fig.skin), chain, joints)


def _rim(skin: Volume) -> Polygon:
    return Polygon(skin.front[-SPOKES_SKIN:, :2]).buffer(0)  # the skin's rim: its last points, in order


def _shown_on(rim: Polygon, depth: Callable[[np.ndarray, np.ndarray], np.ndarray], chain: ArmChain,
              joints: Joints) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
    path, radii = arm_line(chain, joints)
    run = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
    dense = np.linspace(0.0, len(path) - 1.0, max(2, math.ceil(run / SHOWN_STEP) + 1))
    line = np.stack([np.interp(dense, np.arange(len(path)), path[:, k]) for k in range(3)], 1)
    size = np.interp(dense, np.arange(len(path)), radii)
    outside = ~contains_xy(rim, line[:, 0], line[:, 1])
    return line, outside | (line[:, 2] - size < depth(line[:, 0], line[:, 1]))


def upper_seen(fig: Figure, chain: ArmChain, joints: Joints) -> np.ndarray:
    """The points of ``chain``'s upper arm and shoulder ball at ``joints`` that show from the front: turned to the lens,
    and outside the skin's rim or in front of its front. Rings of :data:`TUCK_RING` points round the middle line from
    the shoulder to the elbow, and the ball on as many meridians; the elbow's points nearer the forearm's bone than the
    upper arm's are the forearm's, which comes out from under the cover."""
    return _upper_seen_on(_rim(fig.skin), front_of(fig.skin), chain, joints)


def _upper_seen_on(rim: Polygon, depth: Callable[[np.ndarray, np.ndarray], np.ndarray], chain: ArmChain,
                   joints: Joints) -> np.ndarray:  # fmt: skip
    path, radii = arm_line(chain, joints)
    centres, sizes = path[: ELBOW_AT + 1], radii[: ELBOW_AT + 1]
    along = np.gradient(centres, axis=0)
    along /= np.maximum(np.linalg.norm(along, axis=1, keepdims=True), 1e-12)
    across = np.cross(along, (0.0, 0.0, 1.0))
    flat = np.linalg.norm(across, axis=1) < 1e-6
    across[flat] = np.cross(along[flat], (1.0, 0.0, 0.0))
    across /= np.linalg.norm(across, axis=1, keepdims=True)
    up = np.cross(along, across)
    turn = np.linspace(0.0, math.tau, TUCK_RING, endpoint=False)
    out = np.cos(turn)[None, :, None] * across[:, None, :] + np.sin(turn)[None, :, None] * up[:, None, :]
    rings = (centres[:, None, :] + sizes[:, None, None] * out).reshape(-1, 3)
    polar = np.linspace(0.0, math.pi, TUCK_RING // 2)[:, None]
    ball = np.stack((np.sin(polar) * np.cos(turn), np.cos(polar) * np.ones_like(turn), np.sin(polar) * np.sin(turn)), 2)
    ball = ball.reshape(-1, 3)
    points = np.concatenate((rings, joints.shoulder + chain.radii[0] * ball))
    facing = np.concatenate((out.reshape(-1, 3), ball))[:, 2] < 0.0
    # the elbow's points nearer the forearm's bone are the forearm's
    upper = _off(points, joints.shoulder, joints.elbow) < _off(points, joints.elbow, joints.wrist)
    shown = ~contains_xy(rim, points[:, 0], points[:, 1]) | (points[:, 2] < depth(points[:, 0], points[:, 1]))
    return points[facing & upper & shown]


def _off(points: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """How far each of ``points`` is from the segment ``a`` to ``b``."""
    ab = b - a
    t = np.clip(((points - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(points - (a + t[:, None] * ab), axis=1)


def _tucked(name: str, chain: ArmChain, rim: Polygon, depth: Callable[[np.ndarray, np.ndarray], np.ndarray],
            tuck: Tuck) -> ArmChain:  # fmt: skip
    """``chain`` with its shoulder set back from its solved depth, :data:`TUCK_STEP` at a time, to the nearest depth at
    which none of its upper arm shows beside ``tuck``'s edge; never past the far end of SHOULDER_BACK, where an arm that
    still shows raises."""
    start = float(chain.shoulder[2])
    steps = max(0, math.ceil((SHOULDER_BACK[1] - start) / TUCK_STEP))
    for k in range(steps + 1):
        z = min(start + k * TUCK_STEP, SHOULDER_BACK[1])
        moved = replace(chain, shoulder=np.array((chain.shoulder[0], chain.shoulder[1], z)))
        seen = _upper_seen_on(rim, depth, moved, reach(moved, moved.rest))
        if not tuck.beside(seen[:, 0]).any():
            return moved
    raise FigureError(f"{name}: the {chain.side} arm's upper arm shows beside the cover's edge at {tuck.edge:.1f} at "
                      f"every depth to {SHOULDER_BACK[1]:.0f}")  # fmt: skip


def arm_pieces(fig: Figure, chain: ArmChain, joints: Joints) -> list[float]:
    """Each separate piece of ``chain`` at ``joints`` that shows from the front (:func:`arm_shown`), its length."""
    return _pieces(*_shown(fig, chain, joints))


def _pieces(line: np.ndarray, shown: np.ndarray) -> list[float]:
    step = np.linalg.norm(np.diff(line[:, :2], axis=0), axis=1)
    both = shown[1:] & shown[:-1]
    pieces: list[float] = []
    for k, on in enumerate(both):
        if on and (k == 0 or not both[k - 1]):
            pieces.append(0.0)
        if on:
            pieces[-1] += float(step[k])
    return [p for p in pieces if p > 0.0]


def _fitted(name: str, chain: ArmChain, rim: Polygon, depth: Callable[[np.ndarray, np.ndarray], np.ndarray],
            target: float) -> ArmChain:  # fmt: skip
    """``chain`` with its shoulder's depth solved within SHOULDER_BACK so that at rest it shows ``target`` long from
    the front, within FIT_TOLERANCE; the nearer the shoulder, the longer the arm shows. Bisected FIT_STEPS times at
    the most; an arm the range cannot bring to ``target`` raises."""

    def at(z: float) -> tuple[ArmChain, float]:
        moved = replace(chain, shoulder=np.array((chain.shoulder[0], chain.shoulder[1], z)))
        return moved, float(sum(_pieces(*_shown_on(rim, depth, moved, reach(moved, moved.rest)))))

    near, far = SHOULDER_BACK
    longest, shortest = at(near)[1], at(far)[1]
    if not shortest <= target <= longest:
        raise FigureError(f"{name}: the {chain.side} arm shows {shortest:.1f} to {longest:.1f} with its shoulder "
                          f"{near:.0f} to {far:.0f} deep, never the flat's {target:.1f}")  # fmt: skip
    for _ in range(FIT_STEPS):
        middle = (near + far) / 2.0
        moved, shown = at(middle)
        if abs(shown - target) <= FIT_TOLERANCE:
            return moved
        near, far = (middle, far) if shown > target else (near, middle)
    raise FigureError(f"{name}: the {chain.side} arm's shoulder depth reached no {target:.1f} in {FIT_STEPS} steps")


@dataclass(frozen=True)
class Figure:
    """One character as clay, in the drawing's reference pixels: its skin (head and body as one surface, each point's
    share of the head in ``weights``), its ears on the head, and its one pair of arms, rigged from the shoulders."""

    name: str
    body: Volume  # the body and the head alone, as the skin is solved from them
    head: Volume
    skin: Volume
    weights: np.ndarray  # per skin vertex: 0 moves with the body, 1 with the head
    ears: tuple[Volume, ...]
    arms: tuple[ArmChain, ArmChain]
    ear_back: float  # how far behind the skin's middle plane the ears' stand
    parts: Parts
    extent: tuple[float, float]  # the least and the most x the figure takes at rest, its arms on its lap


def _blobs(layers: Sequence[Layer], colours: set[str], height: float, soften: float):
    """A relief function: ``height`` over the layers in ``colours``, softened at their edges."""
    picked = [flatten(s) for s, c in layers if c in colours]
    if not picked:
        return None
    lo = np.min([p.min(0) for p in picked], axis=0) - 20
    hi = np.max([p.max(0) for p in picked], axis=0) + 20
    box = Box(float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]))
    per = 2.0
    field = np.zeros(tuple(reversed(box.size(per))))
    for outline in picked:
        inside = _mask(outline, box, per).astype(float)
        field = np.maximum(
            field, ndimage.gaussian_filter(np.sqrt(ndimage.distance_transform_edt(inside) / per), soften)
        )
    field = field / float(np.max(field)) * height

    def bump(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        return ndimage.map_coordinates(field, [(y - box.y0) * per - 0.5, (x - box.x0) * per - 0.5], order=1, cval=0.0)

    return bump


@cache
def figure(rig, tuck: Tuck | None = None) -> Figure:
    """``rig`` as clay, with the arm on ``tuck``'s side tucked under the room's cover. The muzzle and the nose are
    modelled; everything else on the face is painted and pressed."""
    name = rig.look.name
    if name not in EAR_DEPTH:
        raise FigureError(f"the clay study builds Mae and Bruno only, not {name!r}")
    parts = parts_of(rig)
    face = list(rig.face())
    nose = _blobs(face, {c for _, c in face if c not in ("ink", "white", rig.look.blush, rig.look.light)}, NOSE, 1.5)
    muzzle = _blobs(face, {rig.look.light}, MUZZLE, 3.0)

    def bump(x, y):
        out = np.zeros_like(x)
        for part in (muzzle, nose):
            if part is not None:
                out = out + part(x, y)
        return out

    head = inflate(parts.head, *HEAD_DEPTH, bump=bump)
    body = inflate(parts.body, *BODY_DEPTH, base=BASE)
    ears = tuple(inflate(ear, *EAR_DEPTH[name]) for ear in parts.ears)
    surface, weights = skin(parts.head, parts.body, BASE, bump)
    depth = front_of(surface)
    flat, rim = flat_rest_arms(rig), _rim(surface)
    left, right = _chains(rig, depth, parts.body)
    arms = (
        _fitted(name, left, rim, depth, flat["left"].length),
        _fitted(name, right, rim, depth, flat["right"].length),
    )
    if tuck is not None:
        first, second = (_tucked(name, c, rim, depth, tuck) if c.side == tuck.side else c for c in arms)
        arms = (first, second)
    xs = [surface.front[:, 0]]
    for chain in arms:
        for meshes in arm_meshes(chain, reach(chain, chain.rest), "coat", "pad").values():
            xs += [mesh.vertices[:, 0] for mesh in meshes]
    every = np.concatenate(xs)
    ear_back = head.depth[1] * 0.35
    return Figure(name, body, head, surface, weights, ears, arms, ear_back, parts,
                  (float(every.min()), float(every.max())))  # fmt: skip


STROKE = -0.9  # reference pixels a fur stroke is pressed into the clay


def textures(paint_layers: Sequence[Layer], raised: Sequence[tuple[Sequence[float], float]], volume: Volume,
             coat: str) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
    """A front's colour picture over its box (the coat under ``paint_layers``) and its normal map (``raised`` over
    the clay's thumb marks)."""
    colour = paint(paint_layers, volume.box, coat, ink=INK, white=WHITE)
    return colour, normal_map(relief(raised, volume.box) + thumbs(volume.box))


def skin_textures(rig, fig: Figure, face: Face) -> tuple[np.ndarray, np.ndarray]:
    """The skin's colour picture and normal map for ``face``, in the drawing's order: the body's belly and fur strokes,
    the head laid over them in its coat with its own strokes, then the face as toon_head draws it."""
    parts = fig.parts
    coat = parts.coat
    dim = _dim(coat, STROKE_DIM)
    layers = face_layers(rig, face)
    painted = [*parts.body_layers, *((s, dim) for s in parts.body_strokes), (parts.head_shape, coat)]
    painted += [(s, dim) for s in parts.head_strokes] + layers
    raised = [(s, STROKE) for s in parts.body_strokes] + [(parts.head_shape, 0.0)]
    raised += [(s, STROKE) for s in parts.head_strokes] + lifts(layers)
    return textures(painted, raised, fig.skin, coat)


def ear_textures(fig: Figure, index: int) -> tuple[np.ndarray, np.ndarray]:
    return textures(fig.parts.ear_layers[index], [], fig.ears[index], fig.parts.coat)


def thumbs(box: Box) -> np.ndarray:
    """The clay's own surface over ``box``: soft thumb dents, in reference pixels."""
    width, height = box.size(TEXELS)
    side = 1 << int(math.ceil(math.log2(max(width, height))))
    return clay.thumbed(side, 1030)[:height, :width] * 0.6


INK, WHITE = "#1b1b22", "#ffffff"  # replaced by the reel's own canvas ink and white: see use_palette


def use_palette(ink: str, white: str) -> None:
    """Paint with the reel canvas's own ink and white."""
    global INK, WHITE
    INK, WHITE = ink, white
