"""Mae and Bruno in clay: each part of the approved rig's drawing inflated into a volume, the face painted from the
rig's own layers.

A part is a filled shape of the drawing: the body's coat, the head's coat, each ear's coat. Its volume is the solution
of a Poisson problem on the shape (zero on the outline, a square root of it as the height), so the outline stays
exactly the drawn one and the surface meets it at a right angle: seen from the lens the clay has the card's
silhouette. The body is solved as if mirrored below its base, so it stands on a flat base as wide and deep as the body
is there. Coordinates are the drawing's reference pixels, x right and y down, with z away from the lens: the front of a
part is at negative z.

The face is the rig's own: its layers (eyes for the pose and the gaze, the mouth or the viseme heard, the lids of a
blink, the teeth) painted in the drawing's order onto a picture laid flat over the head's front, and the same layers
given relief in a normal map: the eyes and teeth stand up, ink lines are pressed in like tool marks, an open mouth is a
hollow. Outline inks and painted shade are left out: the clay's own volume and the room's key give both.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache

import numpy as np
from PIL import Image, ImageDraw
from scipy import interpolate, ndimage, sparse
from scipy.sparse.linalg import spsolve
from shapely.geometry import Polygon
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


def _rays(outline: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """How far from ``centre`` each spoke meets ``outline``: the first crossing, so a shape that is not star-shaped from
    there is cut along the spoke rather than folded."""
    angles = np.linspace(0.0, math.tau, SPOKES, endpoint=False)
    a, b = outline, np.roll(outline, -1, axis=0)
    edge = b - a
    reach = np.empty(SPOKES)
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


def inflate(outline: np.ndarray, front: float, back: float, *, base: float | None = None, bump=None) -> Volume:
    """``outline`` as clay, standing ``front`` times its inradius toward the lens and ``back`` away. With ``base`` (a
    reference y) the part is solved as mirrored there and cut flat on it, so it stands on that line. ``bump(x, y)``
    adds reference pixels of relief to the front."""
    shape = Polygon(outline).buffer(0)
    if base is not None:
        mirrored = np.stack((outline[:, 0], 2 * base - outline[:, 1]), 1)
        shape = unary_union([shape, Polygon(mirrored).buffer(0)]).buffer(0.5).buffer(-0.5)
    if shape.geom_type != "Polygon":
        raise FigureError(f"a part is one piece, got {shape.geom_type}")
    whole = np.array(shape.exterior.coords)[:-1]
    x0, y0 = whole.min(0) - 2
    x1, y1 = whole.max(0) + 2
    box = Box(float(x0), float(y0), float(x1), float(y1))
    per = 1.0
    inside = _mask(whole, box, per)
    field = swell(inside)
    inradius = float(ndimage.distance_transform_edt(inside).max()) / per
    peak = np.unravel_index(np.argmax(field), field.shape)
    centre = np.array((box.x0 + (peak[1] + 0.5) / per, box.y0 + (peak[0] + 0.5) / per))
    reach = _rays(whole, centre)
    rho = 1.0 - (1.0 - np.linspace(0.0, 1.0, RINGS + 1)[1:]) ** 1.6  # rings close up toward the outline
    angles = np.linspace(0.0, math.tau, SPOKES, endpoint=False)
    direction = np.stack((np.cos(angles), np.sin(angles)), 1)
    flat = centre + (rho[:, None, None] * reach[None, :, None]) * direction[None, :, :]
    flat = np.concatenate((centre[None, :], flat.reshape(-1, 2)))
    sample = ndimage.map_coordinates(
        field, [(flat[:, 1] - box.y0) * per - 0.5, (flat[:, 0] - box.x0) * per - 0.5], order=1
    )
    sample[-SPOKES:] = 0.0  # the outline itself: exactly on the drawing's line
    sample = np.clip(sample, 0.0, 1.0)
    lift = np.zeros(len(flat)) if bump is None else np.asarray(bump(flat[:, 0], flat[:, 1]), float)
    zf = -(front * inradius * sample + lift * np.minimum(sample * 4.0, 1.0))
    zb = back * inradius * sample
    xy = flat.copy()
    under = np.zeros(len(flat), bool)
    if base is not None:
        under = xy[:, 1] > base
        xy[under, 1] = base
    triangles = [(0, 1 + (k + 1) % SPOKES, 1 + k) for k in range(SPOKES)]
    triangles += [(1 + t[0], 1 + t[2], 1 + t[1]) for t in clay._sheet(RINGS, SPOKES, True)]
    tris = np.array(triangles, int)
    tris = _wound(flat, tris)
    front_points = np.column_stack((xy, zf))
    back_points = np.column_stack((xy, zb))
    if _vertex_normals(front_points, tris)[0, 2] > 0:  # the middle of the front faces the lens: -z
        tris = tris[:, ::-1].copy()
    nf = _vertex_normals(front_points, tris)
    nb = -_vertex_normals(back_points, tris)
    rim = np.arange(len(flat) - SPOKES, len(flat))
    out = np.column_stack((direction, np.zeros(SPOKES)))
    nf[rim], nb[rim] = out, out
    nf[under], nb[under] = (0.0, 1.0, 0.0), (0.0, 1.0, 0.0)
    return Volume(
        front=front_points,
        back=back_points,
        front_normals=nf,
        back_normals=nb,
        triangles=tris,
        uv=box.uv(flat),
        box=box,
        depth=(float(-zf.min()), float(zb.max())),
    )


# --- the figure -------------------------------------------------------------------------------------------------------

HEAD_DEPTH = (0.78, 0.62)  # front and back, times the part's inradius: a round head
BODY_DEPTH = (0.55, 0.45)
EAR_DEPTH = {"bear": (0.42, 0.42), "rabbit": (0.24, 0.24)}
MUZZLE, NOSE = 9.0, 7.0  # reference pixels the bear's muzzle and either nose stand off the head
HEAD_SINK = 0.6  # the share of the chest's depth under the chin the head stands forward by: the chin sits on the chest
BASE = 832.0  # the bust's lowest drawn row: the sofa room shows it whole, its base on the cushion


@dataclass(frozen=True)
class Figure:
    """One character as clay, in the drawing's reference pixels: what moves with the body, what moves with the head,
    and where the head sits in front of the body."""

    name: str
    body: Volume
    head: Volume
    ears: tuple[Volume, ...]
    head_forward: float  # reference pixels the head's middle plane stands in front of the body's
    ear_back: float  # and how far behind the head's middle plane the ears' stand
    parts: Parts


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
def figure(rig) -> Figure:
    """``rig`` as clay. The muzzle and the nose are modelled; everything else on the face is painted and pressed."""
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
    # The drawing lays the head over the body: in clay the head stands forward of the body by a share of the chest's
    # depth under it, so the chin rests on the chest and the head reads in front of it, as the drawing shows.
    overlap = Polygon(parts.head).intersection(Polygon(parts.body))
    forward = 0.0
    if not overlap.is_empty:
        rows = body.front[:, :2]
        lo = np.array(overlap.bounds[:2])
        hi = np.array(overlap.bounds[2:])
        near = (rows >= lo).all(1) & (rows <= hi).all(1)
        forward = float(-body.front[near, 2].min()) * HEAD_SINK if near.any() else 0.0
    ear_back = head.depth[1] * 0.35
    return Figure(name, body, head, ears, forward, ear_back, parts)


# --- the arms at rest ---------------------------------------------------------------------------------------------

LIMB_DEPTH = (0.5, 0.35)  # front and back, times the part's inradius: a forearm and a paw are flatter than a head
LIMB_SINK = 0.25  # the share of a limb's back pressed into what it lies on
ARMS = ("desk",)  # the arms poses the study models: the reel's every act has its paws on the lap


@dataclass(frozen=True)
class Limb:
    """One part of the arms a pose draws at rest: a forearm or a paw, laid on the body (and a paw on its forearm),
    with the layers painted on it."""

    volume: Volume
    layers: tuple[Layer, ...]


def _resting(layers: Sequence[Layer], coat: str) -> list[tuple[np.ndarray, list[Layer]]]:
    """The arms' layers as parts: each coat-coloured fill starts one, the colours and short ink strokes after it lie on
    it, the ink outlines are left to the volume."""
    parts: list[tuple[np.ndarray, list[Layer]]] = []
    for shape, colour in layers:
        if colour == coat:
            parts.append((flatten(shape), []))
        elif colour == "ink" and len(shape) > OUTLINE_POINTS:
            continue
        elif not parts:
            raise FigureError(f"an arm's {colour} layer comes before any arm")
        else:
            parts[-1][1].append((shape, colour))
    if not parts:
        raise FigureError("the pose draws no arm")
    return parts


def _laid(volume: Volume, under) -> Volume:
    """``volume`` laid on the surface ``under(x, y)`` (the depth of what it rests on, at each point of the drawing):
    its back pressed :data:`LIMB_SINK` of the way in, its rim on that surface."""
    xy = volume.front[:, :2]
    zb = volume.back[:, 2]
    at = under(xy[:, 0], xy[:, 1]) - zb * (1.0 - LIMB_SINK)
    front = np.column_stack((xy, volume.front[:, 2] + at))
    back = np.column_stack((xy, zb + at))
    nf = _vertex_normals(front, volume.triangles)
    nb = -_vertex_normals(back, volume.triangles)
    rim = slice(len(xy) - SPOKES, len(xy))
    nf[rim], nb[rim] = volume.front_normals[rim], volume.back_normals[rim]
    depth = (float(-front[:, 2].min()), float(back[:, 2].max()))
    return Volume(front, back, nf, nb, volume.triangles, volume.uv, volume.box, depth)


def _surface(body: np.ndarray, over: Sequence[np.ndarray]):
    """The depth of the clay at any point of the drawing seen from the front: the body's front (linear inside it, the
    nearest outside), or any part in ``over`` that stands in front of it there."""
    inside = interpolate.LinearNDInterpolator(body[:, :2], body[:, 2])
    nearest = interpolate.NearestNDInterpolator(body[:, :2], body[:, 2])
    parts = [interpolate.LinearNDInterpolator(p[:, :2], p[:, 2]) for p in over]

    def depth(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        z = inside(x, y)
        missing = np.isnan(z)
        if missing.any():
            z[missing] = nearest(x[missing], y[missing])
        for part in parts:
            z = np.fmin(z, part(x, y))  # nearer the lens is less deep; outside a part it has no say
        return z

    return depth


@cache
def limbs(rig, arms: str) -> tuple[Limb, ...]:
    """The arms ``rig``'s pose draws at rest for ``arms``, as clay lying on the body: a paw over its forearm."""
    if arms not in ARMS:
        raise FigureError(f"the clay study models the arms poses {ARMS}, not {arms!r}")
    under, over = _arms(rig.look, arms, 0)
    if over:
        raise FigureError(f"the {arms} pose draws arms over the face, which the clay study does not model")
    fig = figure(rig)
    out: list[Limb] = []
    for outline, layers in _resting(under, rig.look.coat):
        laid = _laid(inflate(outline, *LIMB_DEPTH), _surface(fig.body.front, [limb.volume.front for limb in out]))
        out.append(Limb(laid, tuple(layers)))
    return tuple(out)


def limb_textures(rig, arms: str, index: int) -> tuple[np.ndarray, np.ndarray]:
    limb = limbs(rig, arms)[index]
    return textures(list(limb.layers), lifts(list(limb.layers)), limb.volume, rig.look.coat)


STROKE = -0.9  # reference pixels a fur stroke is pressed into the clay


def textures(paint_layers: Sequence[Layer], raised: Sequence[tuple[Sequence[float], float]], volume: Volume,
             coat: str) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
    """A front's colour picture over its box (the coat under ``paint_layers``) and its normal map (``raised`` over
    the clay's thumb marks)."""
    colour = paint(paint_layers, volume.box, coat, ink=INK, white=WHITE)
    return colour, normal_map(relief(raised, volume.box) + thumbs(volume.box))


def head_textures(rig, fig: Figure, face: Face) -> tuple[np.ndarray, np.ndarray]:
    """The head's colour picture and normal map for ``face``: its fur strokes, then the face as toon_head draws it."""
    coat = fig.parts.coat
    strokes = [(s, _dim(coat, STROKE_DIM)) for s in fig.parts.head_strokes]
    layers = face_layers(rig, face)
    raised = [(s, STROKE) for s in fig.parts.head_strokes] + lifts(layers)
    return textures(strokes + layers, raised, fig.head, coat)


def body_textures(fig: Figure) -> tuple[np.ndarray, np.ndarray]:
    coat = fig.parts.coat
    strokes = [(s, _dim(coat, STROKE_DIM)) for s in fig.parts.body_strokes]
    raised = [(s, STROKE) for s in fig.parts.body_strokes]
    return textures(list(fig.parts.body_layers) + strokes, raised, fig.body, coat)


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
