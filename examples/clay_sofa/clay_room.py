"""The clay figures in the sofa room: posed on each frame from the reel's performance, seen by the room's own cameras,
rendered in three passes and laid into the room's plates.

    P  the figures on stand-ins of the sofa, path traced: their clay, and the shadow and bounce they put on the sofa
    K  the same, rastered flat: the figures white, the sofa black, so the sofa covers what stands behind it
    B  the stand-ins alone, path traced: the sofa without the figures, to measure what they changed on it

The room's back plate times P/B on the sofa is the plate with the figures' shadow on it; the figures from P over that,
where K says they are seen, is the frame. The room's cel plates are never redrawn: they are srlocations' (pinned) and
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
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import clay_figure as cf
import numpy as np
from performance import Arm, Frame
from PIL import Image
from scipy import ndimage

from srstudio import clay, plates
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
    ring = []
    for qx, qy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for a in np.linspace(start, start + 90, 7):
            ring.append((ox + r * math.cos(math.radians(a)), oy + r * math.sin(math.radians(a)), a))
    n = len(ring)
    verts, norms, tris = [], [], []
    for z in (cz - d / 2, cz + d / 2):  # the sides, smooth round the corners
        for x, y, a in ring:
            verts.append(engine((x, y, z)))
            norms.append((math.cos(math.radians(a)), -math.sin(math.radians(a)), 0.0))
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
    """The seat, the arm, the base and the back, at lounge_plates' sizes and places (its back() and seat())."""
    return (
        slab("stand-in", (2.6, 0.76, 0.3), 0.08, (-1.37, 0.597, 0.68)),
        slab("stand-in", (2.4, 0.205, 0.58), 0.016, (-1.4, 0.1475, 0.31)),
        slab("stand-in", (2.3, 0.127, 0.6), 0.03, (-1.28, 0.3105, 0.3)),
        slab("stand-in", (0.19, 0.61, 0.5), 0.075, (-0.095, 0.345, 0.23)),
    )


CUSHION_TOP = 0.3105 + 0.127 / 2
ARM_INNER = -0.095 - 0.19 / 2  # the arm's inner face, metres: nothing sits through it


# --- where the clay sits ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Seat:
    """Where one figure sits: the room point under the middle of its base, and centimetres per reference pixel."""

    at: tuple[float, float, float]  # engine centimetres
    per: float
    mirror: bool


def seat_of(
    fig: cf.Figure,
    card_seat,
    lens: Camera,
    card_px_per_ref: float,
    mirror: bool,
    back_at: float,
    right: float | None = None,
) -> Seat:
    """The seat of a figure that, through the two-shot ``lens``, lands on the column of the card's seat point
    ``card_seat`` (metres) and stands as tall on screen as the card at ``card_px_per_ref`` frame pixels to the reference
    pixel, its back at depth ``back_at`` (metres); with ``right``, moved left as far as it takes for its widest row to
    end there. The size sets the depth and the depth the size, so a few rounds settle both."""
    ex, ez = lens.position[0] / 100.0, lens.position[2] / 100.0
    xs = fig.body.front[:, 0]
    reach = (SEAT_X - xs.min()) if mirror else (xs.max() - SEAT_X)
    per = card_px_per_ref / pixels_per_metre(card_seat, lens)
    x = z = 0.0
    for _ in range(8):
        z = back_at - fig.body.depth[1] * per
        x = ex + (card_seat[0] - ex) * (z - ez) / (card_seat[2] - ez)
        if right is not None:
            x = min(x, right - reach * per)
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


def chains(rig, frame: Frame, mirror: bool) -> tuple[np.ndarray, np.ndarray]:
    """The 2D transforms toon_head's nested groups put on the body and on the head at ``frame``, in reference pixels:
    pair (mirror, gasp, jump) · lean · breath, then turn · nod · idle · lift for the head."""
    seat = (SEAT_X, PAIR_Y)
    pair = _shift(0.0, frame.lift) @ _turn(frame.tilt, seat)
    if mirror:
        pair = pair @ _scale(-1.0, 1.0, seat)
    body = pair @ _turn(frame.lean, BODY_PIVOT) @ _scale(1.0, 1.0 + rig.style.breath_scale * frame.breath, BODY_PIVOT)
    neck = rig.neck
    head = body @ _turn(frame.turn, neck)
    head = head @ _shift(0.0, frame.nod) @ _turn(frame.roll, neck)
    head = head @ _shift(0.0, frame.idle_y) @ _turn(frame.idle_roll, neck)
    head = head @ _shift(0.0, -frame.breath * rig.style.breath_px)
    return body, head


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
    about = np.array([rig.neck[0], rig.neck[1], -fig.head_forward])
    m = np.eye(4)
    m[:3, :3] = turn @ nod
    m[:3, 3] = about - m[:3, :3] @ about
    return m


def _place(points: np.ndarray, normals: np.ndarray | None, m: np.ndarray, seat: Seat):
    local = points @ m[:3, :3].T + m[:3, 3]
    world = np.array(seat.at) + seat.per * (local - (SEAT_X, cf.BASE, 0.0))
    if normals is None:
        return world, None
    turned = normals @ np.linalg.inv(m[:3, :3])  # the inverse transpose, row-wise
    turned /= np.linalg.norm(turned, axis=1, keepdims=True)
    return world, turned


def _mesh(material: str, points, normals, triangles, uvs, m: np.ndarray, seat: Seat) -> clay.Mesh:
    world, facing = _place(points, normals, m, seat)
    tris = triangles if np.linalg.det(m[:3, :3]) > 0 else triangles[:, ::-1]
    return clay.Mesh(material, world, facing, np.ascontiguousarray(tris), uvs)


def _shifted(volume: cf.Volume, dz: float) -> tuple[np.ndarray, np.ndarray]:
    return volume.front + (0.0, 0.0, dz), volume.back + (0.0, 0.0, dz)


TILE = 300.0  # reference pixels to one tile of the clay's thumb marks on the back of a part


def posed(who: str, rig, fig: cf.Figure, frame: Frame, seat: Seat, coat_arm: str) -> tuple[clay.Mesh, ...]:
    """Every mesh of ``who`` at ``frame``, in the room."""
    body2, head2 = chains(rig, frame, seat.mirror)
    body_m = _lift3(body2)
    head_m = _lift3(head2) @ head_swivel(rig, fig, frame)
    face = cf.Face(frame.eyes, frame.gaze, frame.blink, frame.mouth, frame.pose_mouth)
    out = []
    v = fig.body
    out.append(_mesh(f"{who}-body", v.front, v.front_normals, v.triangles, v.uv, body_m, seat))
    out.append(_mesh(f"{who}-coat", v.back, v.back_normals, v.triangles[:, ::-1], v.back[:, :2] / TILE, body_m, seat))
    for k, limb in enumerate(cf.limbs(rig, frame.pose_arms)):  # the paws on the lap ride the body
        v = limb.volume
        out.append(_mesh(f"{who}-limb{k}-{frame.pose_arms}", v.front, v.front_normals, v.triangles, v.uv, body_m, seat))
        out.append(
            _mesh(f"{who}-coat", v.back, v.back_normals, v.triangles[:, ::-1], v.back[:, :2] / TILE, body_m, seat)
        )
    front, back = _shifted(fig.head, -fig.head_forward)
    h = fig.head
    out.append(_mesh(f"{who}-face-{face.key()}", front, h.front_normals, h.triangles, h.uv, head_m, seat))
    out.append(_mesh(f"{who}-coat", back, h.back_normals, h.triangles[:, ::-1], back[:, :2] / TILE, head_m, seat))
    for k, ear in enumerate(fig.ears):
        front, back = _shifted(ear, -fig.head_forward + fig.ear_back)
        out.append(_mesh(f"{who}-ear{k}", front, ear.front_normals, ear.triangles, ear.uv, head_m, seat))
        out.append(
            _mesh(f"{who}-coat", back, ear.back_normals, ear.triangles[:, ::-1], back[:, :2] / TILE, head_m, seat)
        )
    for arm in frame.arms:  # the two-shot draws his raised arms in the shot, not in his groups: they do not lean
        out.append(
            _arm(f"{who}-arm", arm, np.eye(4) if not seat.mirror else _lift3(_scale(-1.0, 1.0, (SEAT_X, 0))), seat)
        )
    return tuple(out)


ARM_DEPTH = 18.0  # reference pixels behind the body's middle plane the raised arms grow from: "behind him"


def _arm(material: str, arm: Arm, m: np.ndarray, seat: Seat) -> clay.Mesh:
    """A raised arm as a clay roll from the shoulder, as long as the drawing's, its end rounded as a paw."""
    model = clay.Model()
    half = arm.width / 2.0 * 0.9
    angle = math.radians(arm.degrees)
    reach = arm.length - half * 0.3
    a = np.array((arm.root[0], arm.root[1], ARM_DEPTH))
    b = a + (reach * math.cos(angle), reach * math.sin(angle), -ARM_DEPTH * 0.6)
    model.capsule(material, tuple(a), tuple(b), half)
    mesh = model.meshes()[0]
    return _mesh(material, mesh.vertices, mesh.normals, mesh.triangles, mesh.vertices[:, :2] / TILE, m, seat)


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
    if key == "body":
        return cf.body_textures(fig)
    if key.startswith("ear"):
        return cf.ear_textures(fig, int(key[3:]))
    if key.startswith("limb"):
        index, arms = key[4:].split("-")
        return cf.limb_textures(rig, arms, int(index))
    return cf.head_textures(rig, fig, face)


def materials(who: str, rig, meshes, arm_coat: str) -> tuple[Material, ...]:
    """The materials ``meshes`` of ``who`` use."""
    out = {}
    for mesh in meshes:
        name = mesh.material
        if name in out or not name.startswith(who):
            continue
        part = name[len(who) + 1 :]
        if part == "coat":
            out[name] = _clay(name, rig.look.coat)
        elif part == "arm":
            out[name] = _clay(name, arm_coat)
        elif part == "body" or part.startswith("ear"):
            out[name] = _clay(name, rig.look.coat, *_textures(rig, part))
        elif part.startswith("limb"):
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


def passes(figures: tuple[clay.Mesh, ...], mats: tuple[Material, ...], lens: Camera, cache_dir: Path, spent: Spent):
    """The three passes of one frame: P, K, and B (which a still camera shares across its frames)."""
    stand = sofa()
    lit = lights()
    p = Plate(WIDTH, HEIGHT, lens, lit, (Placed(stand), Placed(figures)), (*mats, STAND_IN))
    masked_figures = tuple(clay.Mesh("mask-on", m.vertices, m.normals, m.triangles) for m in figures)
    masked_sofa = tuple(clay.Mesh("mask-off", m.vertices, m.normals, m.triangles) for m in stand)
    k = Plate(WIDTH, HEIGHT, lens, (FILL,), (Placed(masked_sofa), Placed(masked_figures)), (MASK_ON, MASK_OFF))
    b = Plate(WIDTH, HEIGHT, lens, lit, (Placed(stand),), (STAND_IN,))
    return (
        render(p, cache_dir, "P", spent),
        render(k, cache_dir, "K", spent, raster=True),
        render(b, cache_dir, "B", spent),
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


def write(path: Path, picture: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(np.clip(picture, 0.0, 1.0) * 255.0).astype(np.uint8), "RGBA").save(path)
