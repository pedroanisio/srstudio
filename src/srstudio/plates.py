"""Plates: path-traced stills, rendered once on demand and cached by what they draw (ADR 0068).

A :class:`Plate` is one camera, one set of lights and some placed meshes. Its digest is the digest of the scene document
it makes, and that document names its meshes and printed textures by digest of their own, so a plate's name is known
without rendering anything and changes exactly when the picture would. Renders land in ``<cache>/<digest>.png``; a
plate that is already there is not rendered again. The engine gives identical bytes for an identical document, so a
rebuild checks itself (:func:`verify`).

A replacement feature is the difference between two plates of the same pose (:func:`patch`): what changed, cut out with
a feathered edge and stored with its place. Printed labels are engine-rendered 2D scenes in a Google font
(:func:`print_png`), typed data with a digest like any other input.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import zlib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from functools import cached_property
from pathlib import Path

import numpy as np
from sr_core.scene import Scene

from . import checks
from .canvas import Canvas
from .clay import Mesh
from .errors import SrstudioError

__all__ = [
    "PRINTABLE",
    "Camera",
    "Light",
    "Line",
    "Material",
    "Patch",
    "Placed",
    "Plate",
    "PlateError",
    "Print",
    "Texture",
    "digest",
    "document",
    "materials_of",
    "patch",
    "pixels",
    "print_name",
    "print_png",
    "render",
    "soften",
    "stage_lights",
    "verify",
    "write_png",
]

PRINTABLE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,:;!?()+-$%'/•")
PRINT_FONT = ("Fredoka", "600", "fredoka-600.ttf", "OFL-1.1")
CLEAR = "#00000000"  # a plate's empty background: the engine writes real alpha
SAMPLES, BOUNCES = 48, 4
RIM_POWER = 220.0
EDGE_LEVEL, DILATE, FEATHER = 8.0, 3, 4  # a patch: levels of change that count, then how far it grows and softens
FOLDER_MODE, FILE_MODE = 0o700, 0o600


class PlateError(SrstudioError, ValueError):
    """A plate that cannot be described or rendered, or a cached file that is not what its name says."""


@dataclass(frozen=True)
class Line:
    """Words on a print: centred at ``x, y`` of the print in pixels, at ``size``."""

    text: str
    x: float
    y: float
    size: float
    color: str

    def __post_init__(self) -> None:
        if not (isinstance(self.text, str) and self.text.strip()):
            raise PlateError(f"a printed line needs words, got {self.text!r}")
        if not set(self.text) <= PRINTABLE:
            raise PlateError(f"prints are in English, got {self.text!r}")
        if not (checks.number(self.size) and self.size > 0):
            raise PlateError(f"a printed line has a size above 0, got {self.size!r}")


@dataclass(frozen=True)
class Print:
    """A printed surface: its background, its pixel size, its words, and a keyline when it has one."""

    background: str
    width: int
    height: int
    lines: tuple[Line, ...]
    border: str = ""


@dataclass(frozen=True, eq=False)
class Texture:
    """A picture made in code, height by width by 4, named by the digest of its pixels."""

    pixels: np.ndarray

    @cached_property
    def sha256(self) -> str:
        return hashlib.sha256(self.pixels.tobytes()).hexdigest()


@dataclass(frozen=True)
class Material:
    """What a mesh is made of. A ``print`` is a texture rendered from typed data, ``color_map`` and ``normal_map`` are
    textures made in code; ``sheen`` is the soft bloom of a surface a hand has been over."""

    id: str
    color: str
    roughness: float = 0.68
    metallic: float = 0.0
    emissive: str = ""
    print: Print | None = None
    color_map: Texture | None = None
    normal_map: Texture | None = None
    normal_scale: float = 1.0
    sheen: str = ""
    subsurface: float = 0.0


@dataclass(frozen=True)
class Light:
    """One light, as the engine reads it."""

    id: str
    kind: str
    color: str
    intensity: float
    at: tuple[float, float, float] | None = None
    radius: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0


@dataclass(frozen=True)
class Camera:
    """A lens at ``position`` aimed at ``target``; ``ao`` is the radius of its ambient occlusion."""

    position: tuple[float, float, float]
    target: tuple[float, float, float]
    fov: float
    ao: float = 10.0


@dataclass(frozen=True, eq=False)
class Placed:
    """Meshes put in the scene at ``at``, turned ``rotation_x`` and ``rotation_y`` degrees about that point."""

    meshes: tuple[Mesh, ...]
    at: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_x: float = 0.0
    rotation_y: float = 0.0


@dataclass(frozen=True, eq=False)
class Plate:
    """One still: ``width`` by ``height``, seen by ``camera``, under ``lights``; ``background`` empty is real alpha."""

    width: int
    height: int
    camera: Camera
    lights: tuple[Light, ...]
    placed: tuple[Placed, ...]
    materials: tuple[Material, ...]
    background: str = CLEAR

    def __post_init__(self) -> None:
        if not (self.width > 0 and self.height > 0):
            raise PlateError(f"a plate has a size, got {self.width}x{self.height}")
        if not self.placed:
            raise PlateError("a plate needs something in it")
        known = {material.id for material in self.materials}
        for placed in self.placed:
            for mesh in placed.meshes:
                if mesh.material not in known:
                    raise PlateError(f"no material {mesh.material!r} on this plate")


def stage_lights(*, warm: bool = True, room: bool = False, rim: bool = False) -> tuple[Light, ...]:
    """The concept study's lighting: one soft key high on the lens's left, a cool fill, a low fill in a room, and for
    a figure a ``rim`` from behind on the key's side that lifts him off the set."""
    key = "#FFE2BA" if warm else "#F7EBD4"
    lights = [
        Light("ambient", "ambient", "#D7E1D7", 0.5),
        Light("key", "sphere-area", key, 150.0, (-420.0, -800.0, -600.0), 240.0),
        Light("fill", "directional", "#AFD4DE", 0.7, yaw=135.0, pitch=-25.0),
    ]
    if room:
        lights.append(Light("low-room-fill", "sphere-area", "#F1E4CD", 60.0, (600.0, -290.0, -900.0), 260.0))
    if rim:
        lights.append(Light("rim", "sphere-area", "#FFE8C4", RIM_POWER, (-560.0, -620.0, 480.0), 150.0))
    return tuple(lights)


def materials_of(meshes: Sequence[Mesh], palette: dict[str, Material]) -> tuple[Material, ...]:
    """The materials ``meshes`` use, once each, in name order."""
    return tuple(palette[name] for name in sorted({mesh.material for mesh in meshes}))


def print_name(printed: Print) -> str:
    """What a printed texture is called: the digest of its definition and its font."""
    text = json.dumps({"print": asdict(printed), "font": PRINT_FONT}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()


def _add_light(lights, light: Light) -> None:
    attrs: dict[str, object] = {"id": light.id, "type": light.kind, "color": light.color, "intensity": light.intensity}
    if light.at is not None:
        attrs.update(x=light.at[0], y=light.at[1], z=light.at[2], radius=light.radius, castShadow=True)
        attrs.update(shadowMapSize=4096, shadowSoftness=10, contactShadows=True)
    elif light.kind == "directional":
        attrs.update(yaw=light.yaw, pitch=light.pitch)
    lights.add_light(**attrs)


def document(plate: Plate) -> bytes:
    """The scene document of ``plate``, naming its meshes and prints by digest."""
    scene = Scene(version="auto")
    scene.add_project(
        width=plate.width,
        height=plate.height,
        fps="1",
        duration=1,
        background=plate.background,
        quality="final",
        antialias3d=4,
        seed=1030,
    )
    assets = scene.add_assets()
    shelf = scene.add_materials()
    comp = scene.add_composition()
    for material in plate.materials:
        attrs: dict[str, object] = {"id": material.id, "baseColor": material.color, "roughness": material.roughness}
        attrs["metallic"] = material.metallic
        if material.emissive:
            attrs["emissive"] = material.emissive
        if material.print is not None:
            attrs["baseColorMap"] = f"prints/{print_name(material.print)}.png"
        if material.color_map is not None:
            attrs["baseColorMap"] = f"textures/{material.color_map.sha256}.png"
        if material.normal_map is not None:
            attrs["normalMap"] = f"textures/{material.normal_map.sha256}.png"
            attrs["normalScale"] = material.normal_scale
        if material.sheen:
            attrs.update(sheenColor=material.sheen, sheenRoughness=0.6)
        if material.subsurface:
            attrs["subsurface"] = material.subsurface
        shelf.add_material(**attrs)  # type: ignore[arg-type]
    seen: set[str] = set()
    serial = 0
    for placed in plate.placed:
        x, y, z = placed.at
        for mesh in placed.meshes:
            name = f"m{mesh.sha256[:16]}"
            if name not in seen:
                seen.add(name)
                assets.add_mesh(id=name, src=f"meshes/{mesh.sha256}.obj", format="obj", sha256=mesh.sha256)
            serial += 1
            comp.add_object3D(
                id=f"o{serial}",
                primitive="mesh",
                material=mesh.material,
                mesh=name,
                x=x,
                y=y,
                z=z,
                rotationX=placed.rotation_x,
                rotationY=placed.rotation_y,
            )
    camera = plate.camera
    target = comp.add_object3D(
        id="aim",
        primitive="sphere",
        material=plate.materials[0].id,
        radius=0.1,
        visible=False,
        x=camera.target[0],
        y=camera.target[1],
        z=camera.target[2],
    )
    lights = scene.add_lights()
    for light in plate.lights:
        _add_light(lights, light)
    comp.add_camera(
        id="camera",
        projection="perspective",
        fov=camera.fov,
        x=camera.position[0],
        y=camera.position[1],
        z=camera.position[2],
        target=target.id,
        ambientOcclusion=True,
        aoRadius=camera.ao,
        aoIntensity=0.45,
        renderer="pathtrace",
        pathSamples=SAMPLES,
        maxBounces=BOUNCES,
        denoise=True,
        exposure=0.12,
    )
    return scene.to_bytes(layout="pretty")


def digest(plate: Plate) -> str:
    """The digest of what ``plate`` draws."""
    return hashlib.sha256(document(plate)).hexdigest()


def _gauss(rows: np.ndarray, sigma: float, axis: int) -> np.ndarray:
    reach = int(sigma * 3)
    weights = np.exp(-0.5 * (np.arange(-reach, reach + 1) / sigma) ** 2)
    weights /= weights.sum()
    return np.apply_along_axis(lambda line: np.convolve(line, weights, mode="same"), axis, rows)


def soften(path: Path, cache: Path, *, sharp_to: int, soft_from: int, sigma: float) -> Path:
    """The picture at ``path`` with the depth of a lens: sharp down to row ``sharp_to``, and blurred by ``sigma`` pixels
    from row ``soft_from`` on, because a surface coming towards the lens goes out of focus. Named by what it was made
    from, so it is made once."""
    if not (0 <= sharp_to < soft_from and sigma > 0):
        raise PlateError(
            f"a falloff needs sharp_to below soft_from and a blur above 0: {sharp_to}, {soft_from}, {sigma}"
        )
    name = hashlib.sha256(f"{path.stem}:{sharp_to}:{soft_from}:{sigma}".encode()).hexdigest()
    target = _folder(cache / "soft") / f"{name}.png"
    if target.exists():
        return target
    rgba = pixels(path).astype(float)
    alpha = rgba[..., 3:] / 255.0
    held = np.concatenate((rgba[..., :3] * alpha, rgba[..., 3:]), axis=2)
    blurred = _gauss(_gauss(held, sigma, 0), sigma, 1)
    ramp = np.clip((np.arange(rgba.shape[0]) - sharp_to) / (soft_from - sharp_to), 0.0, 1.0)[:, None, None]
    mixed = held * (1.0 - ramp) + blurred * ramp
    cover = np.maximum(mixed[..., 3:] / 255.0, 1e-6)
    out = np.concatenate((np.clip(mixed[..., :3] / cover, 0.0, 255.0), mixed[..., 3:]), axis=2)
    return write_png(target, np.round(out).astype(np.uint8))


def _folder(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, FOLDER_MODE)
    return path


def _keep(tmp: Path, target: Path) -> Path:
    """``tmp`` at ``target``, whole or not at all, mode 600."""
    os.chmod(tmp, FILE_MODE)
    os.replace(tmp, target)
    return target


def _engine_render(engine: Path, source: Path, out: Path) -> None:
    """Render frame 0 of ``source``, from its own folder because a document's files are relative to it."""
    done = subprocess.run(
        [str(Path(engine).resolve()), "render", source.name, "--time", "0", "--output", str(out.resolve()), "--strict"],
        cwd=source.parent,
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        raise PlateError(f"the engine could not render {source.name}: {done.stderr.strip()[-600:]}")


def print_png(printed: Print, *, engine: Path, cache: Path, fonts: Path) -> Path:
    """The texture of ``printed``, rendered once. Everything on it is in :data:`PRINT_FONT`, a Google Font."""
    folder = _folder(cache / "prints")
    out = folder / f"{print_name(printed)}.png"
    if out.exists():
        return out
    family, weight, name, license_ = PRINT_FONT
    font = (fonts / name).read_bytes()
    with tempfile.TemporaryDirectory(dir=cache) as work:
        root = Path(work)
        (root / name).write_bytes(font)
        scene = Scene(version="auto")
        scene.add_project(
            width=printed.width, height=printed.height, fps="1", duration=1, background=printed.background, seed=1030
        )
        cv = Canvas(scene, font_asset="print", width=printed.width, height=printed.height)
        cv.assets.add_font(
            id="print",
            src=name,
            sha256=hashlib.sha256(font).hexdigest(),
            family=family,
            weight=weight,
            license=license_,
        )
        if printed.border:
            inset = max(printed.width, printed.height) * 0.02
            wide, tall = printed.width - inset * 2, printed.height - inset * 2
            cv.rect(cv.comp, inset, inset, wide, tall, "#00000000", printed.border, inset * 0.6, inset * 2)
        for number, line in enumerate(printed.lines):
            tall = round(line.size * 1.6)
            x, y = line.x - printed.width / 2, line.y - tall / 2
            cv.text(cv.comp, f"line-{number}", line.text, x, y, printed.width, tall, line.size, line.color)
        source = root / "print.scene.xml"
        source.write_bytes(scene.to_bytes(layout="pretty"))
        tmp = root / "print.png"
        _engine_render(engine, source, tmp)
        shutil.move(tmp, out)
    os.chmod(out, FILE_MODE)
    return out


def _lay_out(plate: Plate, cache: Path, engine: Path, fonts: Path) -> None:
    """Put what ``plate`` names into the cache: its meshes, and its prints, rendered on the way."""
    meshes = _folder(cache / "meshes")
    for placed in plate.placed:
        for mesh in placed.meshes:
            target = meshes / f"{mesh.sha256}.obj"
            if not target.exists():
                tmp = target.with_suffix(f".{os.getpid()}.tmp")
                tmp.write_bytes(mesh.obj)
                _keep(tmp, target)
    textures = _folder(cache / "textures")
    for material in plate.materials:
        if material.print is not None:
            print_png(material.print, engine=engine, cache=cache, fonts=fonts)
        for texture in (material.color_map, material.normal_map):
            if texture is not None and not (textures / f"{texture.sha256}.png").exists():
                write_png(textures / f"{texture.sha256}.png", texture.pixels)


def render(plate: Plate, *, engine: Path, cache: Path, fonts: Path) -> Path:
    """``<cache>/<digest>.png``, rendered only when it is missing."""
    _folder(cache)
    out = cache / f"{digest(plate)}.png"
    if out.exists():
        return out
    return _render_to(plate, out, engine, cache, fonts)


def _render_to(plate: Plate, out: Path, engine: Path, cache: Path, fonts: Path) -> Path:
    _lay_out(plate, cache, engine, fonts)
    source = cache / f"{out.stem}.scene.xml"
    source.write_bytes(document(plate))
    tmp = cache / f"{out.stem}.{os.getpid()}.png"
    try:
        _engine_render(engine, source, tmp)
        return _keep(tmp, out)
    finally:
        source.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)


def verify(plate: Plate, *, engine: Path, cache: Path, fonts: Path) -> str:
    """Render ``plate`` again beside its cached file and refuse any difference: returns the sha256 of its pixels."""
    kept = render(plate, engine=engine, cache=cache, fonts=fonts)
    again = _render_to(plate, cache / f"{kept.stem}.again.png", engine, cache, fonts)
    first, second = pixels(kept), pixels(again)
    again.unlink()
    if first.shape != second.shape or not np.array_equal(first, second):
        raise PlateError(f"plate {kept.stem} did not render to the same pixels twice")
    return hashlib.sha256(first.tobytes()).hexdigest()


def pixels(png: Path) -> np.ndarray:
    """The RGBA pixels of ``png``, height by width by 4."""
    done = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(png),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    width, height = (int(part) for part in done.stdout.strip().split(","))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, np.uint8).reshape(height, width, 4)


def write_png(path: Path, rgba: np.ndarray) -> Path:
    """``rgba`` as an 8-bit PNG, the same bytes for the same pixels, mode 600."""
    height, width = rgba.shape[:2]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    rows = b"".join(b"\0" + row.tobytes() for row in rgba.astype(np.uint8))
    body = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", body) + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b"")
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_bytes(data)
    return _keep(tmp, path)


def _spread(mask: np.ndarray, reach: int) -> np.ndarray:
    """``mask`` box-blurred by ``reach`` pixels each way, along both axes."""
    if reach <= 0:
        return mask
    width = 2 * reach + 1
    out = mask
    for axis in (0, 1):
        total = np.cumsum(np.insert(out, 0, 0.0, axis=axis), axis=axis)
        size = out.shape[axis]
        hi, lo = np.minimum(np.arange(size) + reach + 1, size), np.maximum(np.arange(size) - reach, 0)
        out = (np.take(total, hi, axis=axis) - np.take(total, lo, axis=axis)) / width
    return out


@dataclass(frozen=True)
class Patch:
    """What differs between two plates: a picture with alpha, its top-left at ``x, y`` of the plate."""

    path: Path
    x: int
    y: int
    width: int
    height: int


def patch(base: Path, over: Path, cache: Path, *, within: tuple[int, int, int, int] | None = None) -> Patch | None:
    """What ``over`` adds to ``base``: its changed pixels, grown and feathered, or ``None`` when nothing changed.

    ``within`` (left, top, right, bottom) keeps only that part of the plate: a face stays on the face."""
    name = hashlib.sha256(f"{base.stem}|{over.stem}|{within}|{EDGE_LEVEL}|{DILATE}|{FEATHER}".encode()).hexdigest()
    folder = _folder(cache / "patches")
    png, facts = folder / f"{name}.png", folder / f"{name}.json"
    if facts.exists():
        place = json.loads(facts.read_text())
        return Patch(png, **place) if place else None
    before, after = pixels(base).astype(float), pixels(over).astype(float)
    change = np.abs(after - before).max(axis=2)
    if within is not None:
        left, top, right, bottom = within
        keep = np.zeros(change.shape, bool)
        keep[top:bottom, left:right] = True
        change = np.where(keep, change, 0.0)
    solid = change >= EDGE_LEVEL
    if not solid.any():
        facts.write_text("null")
        return None
    grown = _spread(solid.astype(float), DILATE) > 0.0
    soft = _spread(grown.astype(float), FEATHER)
    soft = np.clip(soft * 2.0, 0.0, 1.0)  # the changed core stays solid; only the rim fades
    ys, xs = np.nonzero(soft)
    top, bottom, left, right = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    picture = after[top:bottom, left:right].copy()
    picture[:, :, 3] = np.round(picture[:, :, 3] * soft[top:bottom, left:right])
    write_png(png, picture)
    place = {"x": left, "y": top, "width": right - left, "height": bottom - top}
    tmp = facts.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(place))
    _keep(tmp, facts)
    return Patch(png, **place)
