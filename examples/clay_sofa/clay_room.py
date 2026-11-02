"""The clay figures in the sofa room: posed on each frame from the reel's performance, seen by the room's own cameras,
rendered in four passes and laid into the room's plates.

    P  the figures on stand-ins of the sofa, path traced: their clay, and the shadow and bounce they put on the sofa
    K  the same, rastered flat: the figures white, the sofa black, so the sofa covers what stands behind it
    B  the stand-ins alone, path traced: the sofa without the figures, to measure what they changed on it
    I  the figures rastered flat with each part in its own colour, the sofa black: where the room's line goes
       (:mod:`clay_ink`)

A figure moves whole (the gasp's tilt and lift, the jump) as the reel moves its card: a turn and a shift, never a
stretch. Within it the skin turns with the body and the head by each point's share, the ears with the head, and the two
arms with the body, their paws wherever the frame sends them. Every engine pass holds the GPU lock (ADR 0171).

The room's back plate times P/B on the sofa is the plate with the figures' shadow on it; the figures from P over that,
where K says they are seen, is the frame. The sofa's arm goes last, off the room's front plate with its own line,
because the flat has it in front of Bruno's right side and the raster passes draw the figures over the stand-ins
whatever stands nearer (:func:`drawn_arm`). The room's cel plates are never redrawn: they are srlocations' (pinned) and
this study only reads them. Units: the room's metres (x right, y up, z away) as srlocations writes them, the engine's
centimetres (x right, y down, z away) as scene-render reads them.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import clay_figure as cf
import clay_ink
import numpy as np
from performance import Frame
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import MultiPoint

from srstudio import clay, gpu, plates
from srstudio.anatomy import Side
from srstudio.plates import Camera, Light, Material, Placed, Plate, Texture

WIDTH, HEIGHT = 1080, 1920
SENSOR_HEIGHT = 24.0  # mm: srlocations' gate; a portrait frame fits its height
AO = 6.0
SINK = 0.016  # metres the clay's base presses into the cushion: as deep as the sofa room sinks its cards (12 px)
SOFA_BACK_FRONT = 0.53  # metres: the sofa back's front face (lounge_plates: depth 0.3 centred at z 0.68)
BACK_CLEARANCE = 0.012  # how far in front of it the clay's back stays
BODY_PIVOT = (185.0, 812.0)  # toon_cast.PIVOT: where a figure leans and breathes
SEAT_X, PAIR_Y = 165.0, 832.0  # toon_pair's seat: the line a mirrored figure turns about, the point a gasp tilts on
KEY_AT = (-1.4, 1.9, -2.0)  # the room's one key, as lounge_plates places it
# calibrated on the stand-ins: at these the sofa back's lit face renders the room plate's own purple (ratio 0.9 to 1.0)
KEY = Light("key", "sphere-area", "#fff3e4", 24.0, None, 45.0)
FILL = Light("ambient", "ambient", "#e8ecf4", 0.08)
CLAY_SHEEN = "#FFE9D2"


def engine(point) -> tuple[float, float, float]:
    """A room point in metres as the engine's centimetres."""
    x, y, z = point
    return (100.0 * x, -100.0 * y, 100.0 * z)


def camera_of(eye, look_at, lens: float) -> Camera:
    """An srlocations camera (eye, aim and lens on its 36x24 gate) as the engine's: its horizontal field of view on
    the portrait frame, which fits the gate's height."""
    focal = lens * HEIGHT / SENSOR_HEIGHT
    fov = 2.0 * math.degrees(math.atan(WIDTH / 2.0 / focal))
    return Camera(engine(eye), engine(look_at), fov, AO)


def project(points, lens: Camera) -> np.ndarray:
    """Engine points to frame pixels through ``lens``, as the engine draws them (srstudio.rafa_host.project)."""
    eye = np.array(lens.position, float)
    forward = np.array(lens.target, float) - eye
    forward /= np.linalg.norm(forward)
    right = np.cross((0.0, 1.0, 0.0), forward)
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    rel = np.asarray(points, float).reshape(-1, 3) - eye
    depth = rel @ forward
    scale = (WIDTH / 2.0) / math.tan(math.radians(lens.fov) / 2.0)
    return np.stack((WIDTH / 2.0 + scale * (rel @ right) / depth, HEIGHT / 2.0 + scale * (rel @ down) / depth), 1)


def pixels_per_metre(point, lens: Camera) -> float:
    eye = np.array(lens.position, float)
    forward = np.array(lens.target, float) - eye
    forward /= np.linalg.norm(forward)
    depth = (np.array(engine(point)) - eye) @ forward
    return 100.0 * (WIDTH / 2.0) / math.tan(math.radians(lens.fov) / 2.0) / depth


# --- the sofa's stand-ins ---------------------------------------------------------------------------------------------


def slab(material: str, size, radius: float, at) -> clay.Mesh:
    """lounge_plates' slab: a rectangle of ``size`` metres rounded by ``radius`` in x and y, flat along z."""
    w, h, d = size
    cx, cy, cz = at
    r = min(radius, w / 2 * 0.99, h / 2 * 0.99)
    ring: list[tuple[float, float, float]] = []
    for qx, qy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for degrees in np.linspace(start, start + 90, 7):
            turn = math.radians(degrees)
            ring.append((ox + r * math.cos(turn), oy + r * math.sin(turn), float(degrees)))
    n = len(ring)
    verts: list[tuple[float, float, float]] = []
    norms: list[tuple[float, float, float]] = []
    tris: list[tuple[int, int, int]] = []
    for z in (cz - d / 2, cz + d / 2):  # the sides, smooth round the corners
        for x, y, angle in ring:
            verts.append(engine((x, y, z)))
            norms.append((math.cos(math.radians(angle)), -math.sin(math.radians(angle)), 0.0))
    for i in range(n):
        j = (i + 1) % n
        tris += [(i, j, n + j), (i, n + j, n + i)]
    for z, sign in ((cz - d / 2, -1.0), (cz + d / 2, 1.0)):  # the two flat ends
        base = len(verts)
        verts.append(engine((cx, cy, z)))
        norms.append((0.0, 0.0, sign))
        for x, y, _ in ring:
            verts.append(engine((x, y, z)))
            norms.append((0.0, 0.0, sign))
        for i in range(n):
            a, b = base + 1 + i, base + 1 + (i + 1) % n
            tris.append((base, a, b) if sign > 0 else (base, b, a))
    return clay.Mesh(material, np.array(verts), np.array(norms), np.array(tris, int))


SOFA = "#7a4a7e"  # _lounge_set.SOFA: the stand-ins bounce the sofa's own colour onto the figures


@cache
def sofa() -> tuple[clay.Mesh, ...]:
    """The back, the base, the cushion and the arm, at lounge_plates' sizes and places (its back() and seat())."""
    return (
        slab("stand-in", (2.6, 0.76, 0.3), 0.08, (-1.37, 0.597, 0.68)),
        slab("stand-in", (2.4, 0.205, 0.58), 0.016, (-1.4, 0.1475, 0.31)),
        slab("stand-in", (2.3, 0.127, 0.6), CUSHION_EDGE, (-1.28, 0.3105, 0.3)),
        slab("stand-in", (0.19, 0.61, 0.5), 0.075, (-0.095, 0.345, 0.23)),
    )


CUSHION_TOP = 0.3105 + 0.127 / 2
CUSHION_EDGE = 0.03  # the cushion's rounded edge, metres: a base sits behind it, on the flat of the cushion
CUSHION_FRONT = 0.3 - 0.6 / 2  # the cushion's front face, metres


# --- where the clay sits ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Seat:
    """Where one figure sits: the room point under the middle of its base, and centimetres per reference pixel."""

    at: tuple[float, float, float]  # engine centimetres
    per: float
    mirror: bool


def seat_of(fig: cf.Figure, card_seat, lens: Camera, card_px_per_ref: float, mirror: bool, back_at: float) -> Seat:
    """The seat of a figure that, through the two-shot ``lens``, lands on the column of the card's seat point
    ``card_seat`` (metres) and stands as tall on screen as the card at ``card_px_per_ref`` frame pixels to the reference
    pixel, its back at depth ``back_at`` (metres). The size sets the depth and the depth the size, so a few rounds
    settle both."""
    ex, ez = lens.position[0] / 100.0, lens.position[2] / 100.0
    per = card_px_per_ref / pixels_per_metre(card_seat, lens)
    x = z = 0.0
    for _ in range(8):
        z = back_at - fig.skin.depth[1] * per
        x = ex + (card_seat[0] - ex) * (z - ez) / (card_seat[2] - ez)
        per = card_px_per_ref / pixels_per_metre((x, CUSHION_TOP, z), lens)
    return Seat(engine((x, CUSHION_TOP - SINK, z)), 100.0 * per, mirror)


def columns(meshes, cell: float = 1.0) -> dict[tuple[int, int], tuple[float, float]]:
    """Where ``meshes`` stand seen along z: for each ``cell``-centimetre column of x and y their vertices fall in,
    the nearest and the farthest depth (engine centimetres)."""
    points = np.concatenate([m.vertices for m in meshes])
    keys = np.floor(points[:, :2] / cell).astype(np.int64)
    cells, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    near = np.full(len(cells), np.inf)
    far = np.full(len(cells), -np.inf)
    np.minimum.at(near, inverse, points[:, 2])
    np.maximum.at(far, inverse, points[:, 2])
    return {(int(a), int(b)): (float(n), float(f)) for (a, b), n, f in zip(cells, near, far, strict=True)}


def clearance(front, back) -> float:
    """Metres between the meshes ``front`` and the meshes ``back`` behind them, over the columns both stand in: the
    least of back's nearest minus front's farthest. Below 0 they pass through each other; with no shared column, inf."""
    a, b = columns(front), columns(back)
    shared = a.keys() & b.keys()
    if not shared:
        return math.inf
    return min(b[k][0] - a[k][1] for k in shared) / 100.0


# --- posing -----------------------------------------------------------------------------------------------------------


def _turn(degrees: float, about) -> np.ndarray:
    """A 3x3 homogeneous 2D rotation, clockwise on screen (y down) as the canvas turns a group."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    ax, ay = about
    return np.array([[c, -s, ax - c * ax + s * ay], [s, c, ay - s * ax - c * ay], [0, 0, 1.0]])


def _shift(dx: float, dy: float) -> np.ndarray:
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1.0]])


def _scale(sx: float, sy: float, about) -> np.ndarray:
    ax, ay = about
    return np.array([[sx, 0, ax - sx * ax], [0, sy, ay - sy * ay], [0, 0, 1.0]])


def figure_motion(frame: Frame, mirror: bool) -> np.ndarray:
    """The whole figure's move at ``frame``, as the reel moves the card: the gasp's tilt turns it about the middle of
    its base, the gasp's and the jump's lift raises it, and Mae is mirrored about the seat line. A turn and a move,
    never a stretch or a shear: the figure rises off the cushion and settles back on it whole."""
    flip = _scale(-1.0, 1.0, (SEAT_X, PAIR_Y)) if mirror else np.eye(3)
    return _shift(0.0, frame.lift) @ _turn(frame.tilt, (SEAT_X, PAIR_Y)) @ flip


def _within(rig, frame: Frame) -> np.ndarray:
    """toon_head's body groups inside the figure: the lean, then the breath."""
    return _turn(frame.lean, BODY_PIVOT) @ _scale(1.0, 1.0 + rig.style.breath_scale * frame.breath, BODY_PIVOT)


def _head(rig, frame: Frame) -> np.ndarray:
    """toon_head's head groups inside the body's: turn · nod · idle, and the breath's lift."""
    neck = rig.neck
    head = _turn(frame.turn, neck) @ _shift(0.0, frame.nod) @ _turn(frame.roll, neck)
    head = head @ _shift(0.0, frame.idle_y) @ _turn(frame.idle_roll, neck)
    return head @ _shift(0.0, -frame.breath * rig.style.breath_px)


def chains(rig, frame: Frame, mirror: bool) -> tuple[np.ndarray, np.ndarray]:
    """The 2D transforms toon_head's nested groups put on the body and on the head at ``frame``, in reference pixels:
    the figure's move (mirror, gasp, jump) · lean · breath, then turn · nod · idle · lift for the head."""
    body = figure_motion(frame, mirror) @ _within(rig, frame)
    return body, body @ _head(rig, frame)


def _lift3(m2: np.ndarray) -> np.ndarray:
    m = np.eye(4)
    m[:2, :2] = m2[:2, :2]
    m[:2, 3] = m2[:2, 2]
    return m


def head_swivel(rig, fig: cf.Figure, frame: Frame) -> np.ndarray:
    """The head's turn in depth: the face sliding ``face_x`` across the head and ``nod * face_slide`` down it, as a
    turn and a nod of a head as deep as the clay's, about the neck on the head's middle plane."""
    depth = fig.head.depth[0]
    yaw = math.atan2(frame.face_x, depth)
    pitch = math.atan2(frame.nod * rig.face_slide, depth)
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    # the front of the head is at -z: a yaw takes it toward +x, a pitch toward +y (down)
    turn = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    nod = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    about = np.array([rig.neck[0], rig.neck[1], 0.0])
    m = np.eye(4)
    m[:3, :3] = turn @ nod
    m[:3, 3] = about - m[:3, :3] @ about
    return m


def _apply(points: np.ndarray, normals: np.ndarray | None, m: np.ndarray):
    moved = points @ m[:3, :3].T + m[:3, 3]
    if normals is None:
        return moved, None
    return moved, normals @ np.linalg.inv(m[:3, :3])  # the inverse transpose, row-wise; not yet unit


def _unit_rows(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)


def _place(points: np.ndarray, normals: np.ndarray | None, m: np.ndarray, seat: Seat):
    local, turned = _apply(points, normals, m)
    world = np.array(seat.at) + seat.per * (local - (SEAT_X, cf.BASE, 0.0))
    return world, None if turned is None else _unit_rows(turned)


def _mesh(material: str, points, normals, triangles, uvs, m: np.ndarray, seat: Seat) -> clay.Mesh:
    world, facing = _place(points, normals, m, seat)
    tris = triangles if np.linalg.det(m[:3, :3]) > 0 else triangles[:, ::-1]
    return clay.Mesh(material, world, facing, np.ascontiguousarray(tris), uvs)


def _shifted(volume: cf.Volume, dz: float) -> tuple[np.ndarray, np.ndarray]:
    return volume.front + (0.0, 0.0, dz), volume.back + (0.0, 0.0, dz)


TILE = 300.0  # reference pixels to one tile of the clay's thumb marks on the back of a part
GASP_TILT = -5.0  # it_autoplayed_data.GASP_TILT: the tilt the reel keys on the gasp alone, at its fullest
FLINCH = (0.0, -42.0, -18.0)  # reference pixels the paws come up toward the chest at the gasp's fullest
RAISED_FORWARD = 24.0  # reference pixels in front of the shoulder a raised paw is held


@dataclass(frozen=True)
class Part:
    """One part of a figure as posed: its meshes, the hand it is if it is one (its side as drawn, before any mirror),
    and the arm chain it belongs to if it does."""

    id: str
    meshes: tuple[clay.Mesh, ...]
    hand: Side | None = None
    chain: str | None = None


def arm_targets(fig: cf.Figure, frame: Frame) -> dict[str, np.ndarray]:
    """Where each paw goes at ``frame``, reference pixels before the body's lean: on the lap at rest; drawn up toward
    the chest as far into the gasp as its tilt is; to the flat card's hand wherever the reel draws one (the Wow, the
    pat), on the chain of the side its shoulder is on. A chain has one paw: two hands on one side are refused."""
    out = {chain.side: chain.rest.copy() for chain in fig.arms}
    share = min(max(frame.tilt / GASP_TILT, 0.0), 1.0)
    for side in out:
        out[side] = out[side] + share * np.array(FLINCH)
    taken: set[str] = set()
    for arm in frame.arms:
        side = "left" if arm.root[0] < SEAT_X else "right"
        if side in taken:
            raise cf.FigureError(f"two hands on the {side} arm at once: a figure has one pair")
        taken.add(side)
        chain = next(c for c in fig.arms if c.side == side)
        turn = math.radians(arm.degrees)
        tip = (arm.root[0] + arm.length * math.cos(turn), arm.root[1] + arm.length * math.sin(turn))
        out[side] = np.array((tip[0], tip[1], chain.shoulder[2] - RAISED_FORWARD))
    return out


def local_parts(who: str, rig, fig: cf.Figure, frame: Frame) -> tuple[Part, ...]:
    """Every part of ``who`` at ``frame`` within the figure, before its move and its seat: the skin (each point turned
    with the body and the head by its share of each), the ears on the head, the two arms on the body."""
    within = _within(rig, frame)
    body_m = _lift3(within)
    head_m = _lift3(within @ _head(rig, frame)) @ head_swivel(rig, fig, frame)
    face = cf.Face(frame.eyes, frame.gaze, frame.blink, frame.mouth, frame.pose_mouth)
    v, w = fig.skin, fig.weights[:, None]
    parts = []
    sheets = []
    for points, normals, tris, uv, material in (
        (v.front, v.front_normals, v.triangles, v.uv, f"{who}-face-{face.key()}"),
        (v.back, v.back_normals, v.triangles[:, ::-1], v.back[:, :2] / TILE, f"{who}-coat"),
    ):
        (pb, nb), (ph, nh) = _apply(points, normals, body_m), _apply(points, normals, head_m)
        sheets.append(clay.Mesh(material, pb * (1.0 - w) + ph * w, _unit_rows(nb * (1.0 - w) + nh * w), tris, uv))
    parts.append(Part(f"{who}-skin", tuple(sheets)))
    for k, ear in enumerate(fig.ears):
        front, back = _shifted(ear, fig.ear_back)
        pf, nf = _apply(front, ear.front_normals, head_m)
        pb, nb = _apply(back, ear.back_normals, head_m)
        parts.append(Part(f"{who}-ear{k}", (
            clay.Mesh(f"{who}-ear{k}", pf, _unit_rows(nf), ear.triangles, ear.uv),
            clay.Mesh(f"{who}-coat", pb, _unit_rows(nb), ear.triangles[:, ::-1].copy(), back[:, :2] / TILE),
        )))  # fmt: skip
    targets = arm_targets(fig, frame)
    for chain in fig.arms:
        made = cf.arm_meshes(chain, cf.reach(chain, targets[chain.side]), f"{who}-arm", f"{who}-pad")
        for name, meshes in made.items():
            moved = []
            for mesh in meshes:
                points, normals = _apply(mesh.vertices, mesh.normals, body_m)
                moved.append(
                    clay.Mesh(mesh.material, points, _unit_rows(normals), mesh.triangles, points[:, :2] / TILE)
                )
            hand = Side.LEFT if chain.side == "left" else Side.RIGHT
            parts.append(Part(f"{who}-{name}-{chain.side}", tuple(moved), hand if name == "paw" else None, chain.side))
    return tuple(parts)


def posed_parts(who: str, rig, fig: cf.Figure, frame: Frame, seat: Seat) -> tuple[Part, ...]:
    """Every part of ``who`` at ``frame``, moved with the whole figure and seated in the room (engine centimetres)."""
    m = _lift3(figure_motion(frame, seat.mirror))
    return tuple(
        Part(
            part.id,
            tuple(_mesh(x.material, x.vertices, x.normals, x.triangles, x.uvs, m, seat) for x in part.meshes),
            part.hand,
            part.chain,
        )  # fmt: skip
        for part in local_parts(who, rig, fig, frame)
    )


def posed(who: str, rig, fig: cf.Figure, frame: Frame, seat: Seat) -> tuple[clay.Mesh, ...]:
    """Every mesh of ``who`` at ``frame``, in the room."""
    return tuple(mesh for part in posed_parts(who, rig, fig, frame, seat) for mesh in part.meshes)


# --- materials --------------------------------------------------------------------------------------------------------

_CLAY_MAP = Texture(clay.normal_tile(clay.thumbed(512, 7), 2.0))


def _clay(name: str, colour: str, colour_map: np.ndarray | None = None, normal_map: np.ndarray | None = None):
    return Material(
        name,
        colour if colour_map is None else "#FFFFFF",
        roughness=0.6,
        color_map=None if colour_map is None else Texture(colour_map),
        normal_map=_CLAY_MAP if normal_map is None else Texture(normal_map),
        normal_scale=0.55 if normal_map is None else 1.0,
        sheen=CLAY_SHEEN,
    )


@cache
def _textures(rig, key: str, face: cf.Face | None = None):
    fig = cf.figure(rig)
    if key.startswith("ear"):
        return cf.ear_textures(fig, int(key[3:]))
    if face is None:
        raise RenderError(f"the skin's pictures need the face it shows ({key})")
    return cf.skin_textures(rig, fig, face)


def materials(who: str, rig, meshes) -> tuple[Material, ...]:
    """The materials ``meshes`` of ``who`` use."""
    out = {}
    fig = cf.figure(rig)
    for mesh in meshes:
        name = mesh.material
        if name in out or not name.startswith(who):
            continue
        part = name[len(who) + 1 :]
        if part in ("coat", "arm"):
            out[name] = _clay(name, rig.look.coat)
        elif part == "pad":
            out[name] = _clay(name, fig.arms[0].pad)
        elif part.startswith("ear"):
            out[name] = _clay(name, rig.look.coat, *_textures(rig, part))
        elif part.startswith("face-"):
            eyes, gaze, blink, mouth, pose_mouth = part[5:].split("-")
            face = cf.Face(eyes, gaze, blink == "shut", mouth, pose_mouth)
            out[name] = _clay(name, rig.look.coat, *_textures(rig, part, face))
        else:
            raise cf.FigureError(f"no material for {name!r}")
    return tuple(out[k] for k in sorted(out))


STAND_IN = Material("stand-in", SOFA, roughness=0.9)
MASK_ON = Material("mask-on", "#000000", roughness=1.0, emissive="#FFFFFF")
MASK_OFF = Material("mask-off", "#000000", roughness=1.0)


# --- rendering --------------------------------------------------------------------------------------------------------


@dataclass
class Spent:
    """What the renders cost: engine wall seconds per pass, and how many ran or came from the cache."""

    seconds: dict
    runs: dict
    cached: dict

    @classmethod
    def new(cls) -> Spent:
        return cls({}, {}, {})

    def add(self, kind: str, seconds: float | None) -> None:
        if seconds is None:
            self.cached[kind] = self.cached.get(kind, 0) + 1
            return
        self.seconds[kind] = round(self.seconds.get(kind, 0.0) + seconds, 3)
        self.runs[kind] = self.runs.get(kind, 0) + 1


def _raster(document: bytes) -> bytes:
    text = document.decode()
    text = text.replace('renderer="pathtrace"', 'renderer="raster"').replace(
        'ambientOcclusion="true"', 'ambientOcclusion="false"'
    )
    text = re.sub(r'exposure="[^"]*"', 'exposure="0"', text)
    return text.encode()


def render(plate: Plate, cache_dir: Path, kind: str, spent: Spent, *, raster: bool = False) -> Path:
    """``plate`` rendered once: the PNG is named by the digest of its document (meshes and textures are named in it by
    theirs) and the engine's."""
    engine_path = Path(os.environ["SRSTUDIO_ENGINE"])
    document = plates.document(plate)
    if raster:
        document = _raster(document)
    engine_sha = _engine_sha(str(engine_path))
    key = hashlib.sha256(engine_sha.encode() + b"\0" + document).hexdigest()
    out = cache_dir / kind / f"{key}.png"
    if out.exists():
        spent.add(kind, None)
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir) as work:
        root = Path(work)
        (root / "meshes").mkdir()
        (root / "textures").mkdir()
        for placed in plate.placed:
            for mesh in placed.meshes:
                target = root / "meshes" / f"{mesh.sha256}.obj"
                if not target.exists():
                    target.write_bytes(mesh.obj)
        for material in plate.materials:
            for texture in (material.color_map, material.normal_map):
                if texture is not None:
                    target = root / "textures" / f"{texture.sha256}.png"
                    if not target.exists():
                        plates.write_png(target, texture.pixels)
        (root / "plate.scene.xml").write_bytes(document)
        with gpu.held():  # one GPU job at a time (ADR 0171); the wait is not the render's
            start = time.perf_counter()
            done = subprocess.run(
                [
                    str(engine_path.resolve()),
                    "render",
                    "plate.scene.xml",
                    "--time",
                    "0",
                    "--output",
                    "plate.png",
                    "--strict",
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )
        seconds = time.perf_counter() - start
        if done.returncode != 0:
            raise RenderError(f"the engine could not render a {kind} pass: {done.stderr.strip()[-800:]}")
        if done.stderr.strip() and "warning" in done.stderr:
            raise RenderError(f"the engine warned on a {kind} pass: {done.stderr.strip()[-800:]}")
        shutil.move(str(root / "plate.png"), out)
    spent.add(kind, seconds)
    return out


class RenderError(RuntimeError):
    """The engine refused or warned on a pass."""


@cache
def _engine_sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lights() -> tuple[Light, ...]:
    return (FILL, Light(KEY.id, KEY.kind, KEY.color, KEY.intensity, engine(KEY_AT), KEY.radius))


def id_materials(parts: Mapping[str, Sequence[Part]]) -> tuple[tuple[clay.Mesh, ...], tuple[Material, ...]]:
    """Every part of every figure in its own flat colour (:func:`clay_ink.id_colour`), lit by nothing but itself: what
    the ink reads to tell where one part ends and another begins. A pad is drawn as its paw."""
    meshes: list[clay.Mesh] = []
    mats: dict[str, Material] = {}
    for who, posed_parts in parts.items():
        for part in posed_parts:
            name = part.id[len(who) + 1 :]
            name = "paw-" + name[4:] if name.startswith("pad-") else name
            material = f"id-{who}-{name}"
            if material not in mats:
                r, g, b = (int(round(v * 255)) for v in clay_ink.id_colour(who, name))
                mats[material] = Material(material, "#000000", roughness=1.0, emissive=f"#{r:02X}{g:02X}{b:02X}")
            meshes += [clay.Mesh(material, m.vertices, m.normals, m.triangles) for m in part.meshes]
    return tuple(meshes), tuple(mats[k] for k in sorted(mats))


def passes(
    parts: Mapping[str, Sequence[Part]], mats: tuple[Material, ...], lens: Camera, cache_dir: Path, spent: Spent
) -> tuple[Path, Path, Path, Path]:
    """The four passes of one frame: P, K, B (which a still camera shares across its frames) and I, the parts' IDs."""
    figures = tuple(mesh for posed_parts in parts.values() for part in posed_parts for mesh in part.meshes)
    stand = sofa()
    lit = lights()
    p = Plate(WIDTH, HEIGHT, lens, lit, (Placed(stand), Placed(figures)), (*mats, STAND_IN))
    masked_figures = tuple(clay.Mesh("mask-on", m.vertices, m.normals, m.triangles) for m in figures)
    masked_sofa = tuple(clay.Mesh("mask-off", m.vertices, m.normals, m.triangles) for m in stand)
    k = Plate(WIDTH, HEIGHT, lens, (FILL,), (Placed(masked_sofa), Placed(masked_figures)), (MASK_ON, MASK_OFF))
    b = Plate(WIDTH, HEIGHT, lens, lit, (Placed(stand),), (STAND_IN,))
    id_meshes, id_mats = id_materials(parts)
    i = Plate(WIDTH, HEIGHT, lens, (FILL,), (Placed(masked_sofa), Placed(id_meshes)), (*id_mats, MASK_OFF))
    return (
        render(p, cache_dir, "P", spent),
        render(k, cache_dir, "K", spent, raster=True),
        render(b, cache_dir, "B", spent),
        render(i, cache_dir, "I", spent, raster=True),
    )


# --- the composite ----------------------------------------------------------------------------------------------------

SHADOW_FLOOR, SHADOW_NOISE, SHADOW_SOFT = 0.22, 0.025, 1.2


def rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.float64) / 255.0


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def shadow(p: np.ndarray, b: np.ndarray, k: np.ndarray) -> np.ndarray:
    """How much the figures darken the sofa: P over B on the sofa where no figure is seen, 1 elsewhere. Below the
    renderer's noise it is 1; it never brightens and never goes below :data:`SHADOW_FLOOR`."""
    if p.shape != b.shape or p.shape[:2] != k.shape[:2]:
        raise RenderError(f"passes of different sizes: {p.shape}, {b.shape}, {k.shape}")
    seen = b[..., 3] > 0.5
    ratio = np.ones(p.shape[:2])
    lum_b = luminance(b[..., :3])
    ok = seen & (lum_b > 0.02)
    ratio[ok] = luminance(p[..., :3])[ok] / lum_b[ok]
    ratio = ndimage.gaussian_filter(ratio, SHADOW_SOFT)
    ratio = np.clip(ratio, SHADOW_FLOOR, 1.0)
    ratio[ratio > 1.0 - SHADOW_NOISE] = 1.0
    return ratio


def coverage(k: np.ndarray) -> np.ndarray:
    """The figures' coverage from the K pass: white where seen, black where the sofa covers them, clear elsewhere."""
    return np.clip(luminance(k[..., :3]) * k[..., 3], 0.0, 1.0)


def composite(back: np.ndarray, p: np.ndarray, k: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The room's back plate with the figures' shadow on it and the figures over it; and the shadow."""
    cover = coverage(k)
    dark = shadow(p, b, k)
    out = back.copy()
    out[..., :3] *= dark[..., None]
    out[..., :3] = out[..., :3] * (1.0 - cover[..., None]) + p[..., :3] * cover[..., None]
    out[..., 3] = np.maximum(out[..., 3], cover)
    return out, dark


ARM_LINE = 14.0  # frame pixels past the stand-in's front face: the drawn arm's own line round it


def drawn_arm(front: np.ndarray, lens: Camera) -> np.ndarray:
    """The sofa's arm off the room's ``front`` plate, seen through ``lens``: the plate wherever the arm stand-in falls
    on the frame (its front face, and any side the lens sees above the cushion, which hides the rest), with its line,
    and clear everywhere else, so the seat strip beside it and a base resting on the cushion stay out."""
    arm = sofa()[-1].vertices
    face = arm[arm[:, 2] < arm[:, 2].min() + 1e-6]
    lo, hi = arm.min(0), arm.max(0)
    cut = np.array([(x, -100.0 * CUSHION_TOP, z) for x in (lo[0], hi[0]) for z in (lo[2], hi[2])])  # engine y is down
    above = np.concatenate((arm[arm[:, 1] <= -100.0 * CUSHION_TOP], cut))  # the stand-in cut at the cushion's top
    hulls = [MultiPoint(project(points, lens)).convex_hull for points in (face, above)]
    shape = hulls[0].union(hulls[1]).buffer(ARM_LINE)
    mask = Image.new("L", (front.shape[1], front.shape[0]), 0)
    ImageDraw.Draw(mask).polygon(list(shape.exterior.coords), fill=255)
    out = front.copy()
    out[..., 3] *= np.asarray(mask, dtype=np.float64) / 255.0
    return out


def over(picture: np.ndarray, top: np.ndarray) -> np.ndarray:
    """``top`` laid over ``picture``."""
    a = top[..., 3:]
    out = picture.copy()
    out[..., :3] = picture[..., :3] * (1.0 - a) + top[..., :3] * a
    out[..., 3] = np.maximum(picture[..., 3], top[..., 3])
    return out


def write(path: Path, picture: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(np.clip(picture, 0.0, 1.0) * 255.0).astype(np.uint8), "RGBA").save(path)
