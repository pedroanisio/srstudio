"""Plates: path-traced stills, rendered once on demand and cached by what they draw (ADR 0068).

A :class:`Plate` is one camera, one set of lights and some placed meshes. Its digest is the digest of the scene document
it makes, and that document names its meshes and printed textures by digest of their own, so a drawing's name is known
without rendering anything. Render artifacts additionally include the engine bytes, actual print font bytes and
compiled print scenes in their identity. They live under ``<cache>/renders/<engine-sha256>/``. Treat returned paths as
opaque; :func:`digest` identifies the drawing, not a rendered file. An unchanged build reuses its artifacts, and
:func:`verify` compares a fresh render with the cached pixels on the selected toolchain.

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
import time
import zlib
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from sr_core.scene import Scene

from . import _bounded_process, checks, gpu
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
    "RenderStats",
    "Texture",
    "digest",
    "document",
    "materials_of",
    "patch",
    "pixels",
    "place",
    "print_name",
    "print_png",
    "render",
    "render_session",
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

# Closed compatibility aliases for authored maps at e15fe9cc (ADR 0107).
# Both raw pixel hash and exact (width, height) must match. New maps never
# acquire a legacy alias; changed pixels or dimensions use the versioned name.
_LEGACY_TEXTURE_SHAPES = {
    '6a00aead39ee1254ab2e90acc73cd7420c75ab031cd76f8db4bd8677f3685504': (256, 256),  # Rafa knit
    '1a1c0dac9348e6391bffbf63814617bf8b45da65c0d9f39d75206547ea192d40': (512, 512),  # Rafa clay
    '163071864c1eadfd510eab6dfed04ec39e17fd32a0290db5f085ae4431ebe8ed': (421, 241),  # Rafa skin
    '401293498f1d1a3ba859623315d8b94b98b72fac0ed2b6aff5fbc0c405bde034': (1024, 1024),  # Pedro scalp
    '5358382f6ff591492fb1401360d884a2a2bf9016db33e5141a7ca243d9a1fbe2': (1024, 768),  # Pedro goatee
}


class PlateError(SrstudioError, ValueError):
    """A plate that cannot be described or rendered, or a cached file that is not what its name says."""


@dataclass
class RenderStats:
    """Observed launch attempts, successful/failed renders and wall seconds inside a render session.

    Cache hits do not launch an engine. Launch errors and timeouts count as failed attempts.
    Changing these reporting fields does not restore the session's invocation budget.
    """

    invocations: int = 0
    completed: int = 0
    failed: int = 0
    engine_seconds: float = 0.0


@dataclass
class _RenderScope:
    maximum: int
    timeout: float
    memory_bytes: int
    stats: RenderStats
    file_bytes: int | None = None
    spent: int = 0


_RENDER_SCOPES: ContextVar[tuple[_RenderScope, ...]] = ContextVar('srstudio_plate_render_scopes', default=())


@contextmanager
def render_session(
    *,
    max_invocations: int = 100,
    timeout: float = 60,
    max_memory_bytes: int = 8 * 1024**3,
    max_file_bytes: int | None = None,
) -> Iterator[RenderStats]:
    """Measure and bound plate/print renderer work in this context, including nested calls.

    Each enclosing session consumes one attempt per engine launch and the shortest
    active timeout and smallest memory limit apply. Memory is a POSIX hard
    per-process virtual-address-space limit, not aggregate RSS or GPU memory.
    Each output stream is capped at 64 KiB; failures stop the owned process group.
    max_file_bytes optionally caps each file written by a renderer process using
    RLIMIT_FSIZE. Nested scopes use the smallest supplied cap; None adds no cap.
    A zero invocation budget permits only cache hits. These limits do not bound
    mesh preparation, image decoding or other renderer entry points.
    """
    if type(max_invocations) is not int or not 0 <= max_invocations <= 10000:
        raise PlateError('max_invocations must be an integer in 0..10000', code='plate.render.limit')
    if not checks.number(timeout) or not 0 < timeout <= 600:
        raise PlateError('timeout must be finite seconds in (0, 600]', code='plate.render.limit')
    if type(max_memory_bytes) is not int or not 1 <= max_memory_bytes <= 1024**4:
        raise PlateError('max_memory_bytes must be an integer in 1..1099511627776', code='plate.render.limit')
    if max_file_bytes is not None and (type(max_file_bytes) is not int or not 1 <= max_file_bytes <= 1024**4):
        raise PlateError('max_file_bytes must be None or an integer in 1..1099511627776', code='plate.render.limit')
    scope = _RenderScope(max_invocations, timeout, max_memory_bytes, RenderStats(), max_file_bytes)
    token = _RENDER_SCOPES.set((*_RENDER_SCOPES.get(), scope))
    try:
        yield scope.stats
    finally:
        _RENDER_SCOPES.reset(token)


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
    """An RGBA8 picture, named by its dimensions and current row-major pixels.

    The caller owns the mutable array. Rendering snapshots it before cache lookup;
    edits between requests change both drawing and render identity.
    """

    pixels: np.ndarray

    @property
    def sha256(self) -> str:
        pixels = self._validated_pixels()
        height, width = pixels.shape[:2]
        raw = pixels.tobytes(order='C')
        legacy = hashlib.sha256(raw).hexdigest()
        if _LEGACY_TEXTURE_SHAPES.get(legacy) == (width, height):
            return legacy
        digest_ = hashlib.sha256(b'srstudio.texture/1.0.0\0' + struct.pack('>II', width, height))
        digest_.update(raw)
        return digest_.hexdigest()

    def _validated_pixels(self) -> np.ndarray:
        pixels = self.pixels
        if (
            type(pixels) is not np.ndarray
            or pixels.ndim != 3
            or pixels.shape[2] != 4
            or pixels.dtype != np.dtype('uint8')
            or any(not 1 <= n <= 2**31 - 1 for n in pixels.shape[:2])
        ):
            raise PlateError(
                'a texture needs a nonempty height-by-width-by-four uint8 array',
                code='plate.texture.pixels',
                path='texture.pixels',
                actual=type(pixels).__name__,
                expected='an RGBA8 numpy.ndarray with PNG-compatible positive dimensions',
                remedy='Supply uint8 RGBA pixels; explicitly convert other formats before constructing the texture.',
            )
        return pixels


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
    """The logical texture name from its definition and declared font metadata, independent of rendering."""
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
    texture_names: dict[int, str] = {}

    def texture_name(texture: Texture) -> str:
        key = id(texture)
        if key not in texture_names:
            texture_names[key] = texture.sha256
        return texture_names[key]

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
            attrs["baseColorMap"] = f"textures/{texture_name(material.color_map)}.png"
        if material.normal_map is not None:
            attrs["normalMap"] = f"textures/{texture_name(material.normal_map)}.png"
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


def place(cv: Canvas, parent, plate: Plate, *, y: float = 0.0):
    """``plate`` as a picture in ``parent``, by name: a drawing's digest needs no render, and its file comes later.
    Two faces can be the same picture, so a plate already on the canvas is shown again from its one asset."""
    name = digest(plate)
    asset = f"plate-{name[:20]}"
    if not any(getattr(node, "id", None) == asset for node in cv.assets.nodes):
        cv.assets.add_image(id=asset, src=f"plates/{name}.png", width=plate.width, height=plate.height)
    return parent.add_layer(id=cv.uid("plate"), asset=asset, x=0, y=y)


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
    scopes = _RENDER_SCOPES.get()
    for scope in scopes:
        if scope.spent >= scope.maximum:
            raise PlateError(
                'plate renderer invocation budget exhausted',
                code='plate.render.budget',
                path='max_invocations',
                actual=scope.spent,
                expected=f'fewer than {scope.maximum} attempts',
                remedy='Reuse cached inputs or explicitly increase the render-session budget.',
            )
    with gpu.held():  # one GPU job at a time; the wait counts against no budget and no engine second
        _timed_render(engine, source, out, scopes)


def _timed_render(engine: Path, source: Path, out: Path, scopes: tuple[_RenderScope, ...]) -> None:
    for scope in scopes:
        scope.spent += 1
        scope.stats.invocations += 1
    start = time.perf_counter()
    completed = False
    try:
        limits = (
            _bounded_process.ProcessLimits(
                timeout=min(s.timeout for s in scopes),
                memory_bytes=min(s.memory_bytes for s in scopes),
                stdout_bytes=65536,
                stderr_bytes=65536,
                file_bytes=min((s.file_bytes for s in scopes if s.file_bytes is not None), default=None),
            )
            if scopes
            else None
        )
        _invoke_renderer(engine, source, out, limits)
        completed = True
    finally:
        elapsed = time.perf_counter() - start
        for scope in scopes:
            scope.stats.engine_seconds += elapsed
            scope.stats.completed += int(completed)
            scope.stats.failed += int(not completed)


def _invoke_renderer(engine: Path, source: Path, out: Path, limits: _bounded_process.ProcessLimits | None) -> None:
    command = (
        str(Path(engine).resolve()),
        'render',
        source.name,
        '--time',
        '0',
        '--output',
        str(out.resolve()),
        '--strict',
    )
    if limits is not None:
        try:
            _bounded_process.run(command, input=b'', limits=limits, cwd=source.parent)
        except _bounded_process.BoundedProcessError as error:
            diagnostic = error.to_dict()
            kind = {'process.timeout': 'timeout', 'process.output': 'output'}.get(diagnostic['code'], 'engine')
            stderr = error.stderr.decode('utf-8', errors='replace')[-600:]
            raise PlateError(
                f'plate renderer {kind} failure: {error}; {stderr}',
                code=f'plate.render.{kind}',
                path=diagnostic['path'],
                actual={'process': diagnostic, 'stderr': stderr},
                expected='a successful render within the declared process limits',
                remedy='Repair renderer inputs or explicitly adjust the finite render-session limits before retrying.',
            ) from error
        return
    try:
        done = subprocess.run(command, cwd=source.parent, capture_output=True, text=True, timeout=None)
    except OSError as error:
        raise PlateError(
            f'cannot execute renderer {engine}: {error}',
            code='plate.render.engine',
            path='engine',
            actual=str(engine),
            expected='an executable scene-render build',
            remedy='Supply a working renderer executable with its required runtime dependencies.',
        ) from error
    if done.returncode != 0:
        raise PlateError(f"the engine could not render {source.name}: {done.stderr.strip()[-600:]}")


def _input_error(path: str, value: Path, error: OSError) -> PlateError:
    return PlateError(
        f'cannot read render {path}: {value}: {error}',
        code='plate.cache.input',
        path=path,
        actual=str(value),
        expected='a readable renderer file or print font',
        remedy='Supply the selected renderer and, for printed materials, the actual PRINT_FONT file.',
    )


def _engine_digest(engine: Path) -> str:
    digest_ = hashlib.sha256()
    try:
        with engine.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest_.update(block)
    except OSError as error:
        raise _input_error('engine', engine, error) from error
    return digest_.hexdigest()


@dataclass(frozen=True)
class _RenderInputs:
    engine: Path
    engine_digest: str
    font: bytes | None
    textures: tuple[tuple[str, Texture], ...] = ()

    def check_engine(self) -> None:
        if _engine_digest(self.engine) != self.engine_digest:
            raise PlateError(
                'renderer changed during rendering; the current artifact was not published',
                code='plate.cache.changed',
                path='engine',
                actual=str(self.engine),
                expected=self.engine_digest,
                remedy='Keep the renderer file immutable for the build, then retry with the selected build.',
            )

    def key(self, kind: str, source: bytes, prints: Sequence[bytes] = ()) -> str:
        textured = kind == 'plate' and bool(self.textures)
        definition: dict[str, object] = {
            'schema': 'srstudio.plate-render/1.1.0' if textured else 'srstudio.plate-render/1.0.0',
            'kind': kind,
            'engine': self.engine_digest,
            'font': hashlib.sha256(self.font).hexdigest() if self.font is not None else None,
            'document': hashlib.sha256(source).hexdigest(),
            'prints': sorted(hashlib.sha256(item).hexdigest() for item in prints),
        }
        if textured:
            definition['textures'] = [
                {'name': name, 'width': texture.pixels.shape[1], 'height': texture.pixels.shape[0]}
                for name, texture in sorted(self.textures)
            ]
        return hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()

    def folder(self, cache: Path) -> Path:
        return _folder(_folder(_folder(cache) / 'renders') / self.engine_digest)


def _render_inputs(engine: Path, fonts: Path, *, printed: bool) -> _RenderInputs:
    engine = Path(engine).absolute()
    engine_digest = _engine_digest(engine)
    font = None
    if printed:
        path = fonts / PRINT_FONT[2]
        try:
            font = path.read_bytes()
        except OSError as error:
            raise _input_error('font', path, error) from error
    return _RenderInputs(engine, engine_digest, font)


def _print_document(printed: Print, font: bytes) -> bytes:
    family, weight, name, license_ = PRINT_FONT
    scene = Scene(version="auto")
    scene.add_project(
        width=printed.width, height=printed.height, fps="1", duration=1, background=printed.background, seed=1030
    )
    cv = Canvas(scene, font_asset="print", width=printed.width, height=printed.height)
    cv.assets.add_font(
        id="print", src=name, sha256=hashlib.sha256(font).hexdigest(), family=family, weight=weight, license=license_
    )
    if printed.border:
        inset = max(printed.width, printed.height) * 0.02
        wide, tall = printed.width - inset * 2, printed.height - inset * 2
        cv.rect(cv.comp, inset, inset, wide, tall, "#00000000", printed.border, inset * 0.6, inset * 2)
    for number, line in enumerate(printed.lines):
        tall = round(line.size * 1.6)
        x, y = line.x - printed.width / 2, line.y - tall / 2
        cv.text(cv.comp, f"line-{number}", line.text, x, y, printed.width, tall, line.size, line.color)
    return scene.to_bytes(layout="pretty")


def _private_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(FILE_MODE)


def _cached_print(source: bytes, inputs: _RenderInputs, folder: Path) -> Path:
    out = folder / f'{inputs.key("print", source)}.png'
    if out.exists():
        return out
    assert inputs.font is not None  # preflight reads the actual font before cache mutation
    with tempfile.TemporaryDirectory(dir=folder) as work:
        root = Path(work)
        _private_bytes(root / PRINT_FONT[2], inputs.font)
        document_ = root / 'print.scene.xml'
        _private_bytes(document_, source)
        tmp = root / "print.png"
        _engine_render(inputs.engine, document_, tmp)
        inputs.check_engine()
        return _keep(tmp, out)


def print_png(printed: Print, *, engine: Path, cache: Path, fonts: Path) -> Path:
    """The print texture cached by its scene, renderer and actual PRINT_FONT bytes."""
    inputs = _render_inputs(engine, fonts, printed=True)
    assert inputs.font is not None
    source = _print_document(printed, inputs.font)
    return _cached_print(source, inputs, inputs.folder(cache))


def _lay_out(plate: Plate, cache: Path, inputs: _RenderInputs, folder: Path, prints: dict[str, bytes]) -> None:
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
    for name, source in prints.items():
        rendered = _cached_print(source, inputs, folder)
        target = _folder(cache / 'prints') / f'{name}.png'
        shutil.copyfile(rendered, target)
        target.chmod(FILE_MODE)
    for name, texture in inputs.textures:
        write_png(textures / f'{name}.png', texture.pixels)


def render(plate: Plate, *, engine: Path, cache: Path, fonts: Path) -> Path:
    """A renderer-owned artifact, rendered only when its complete input identity is missing."""
    inputs, source, prints = _prepare(plate, engine, fonts)
    folder = inputs.folder(cache)
    out = folder / f'{inputs.key("plate", source, tuple(prints.values()))}.png'
    if out.exists():
        return out
    return _render_to(plate, out, inputs, folder, source, prints)


def _prepare(plate: Plate, engine: Path, fonts: Path) -> tuple[_RenderInputs, bytes, dict[str, bytes]]:
    snapshots: dict[int, Texture] = {}
    materials = []
    for material in plate.materials:
        maps = {}
        for name in ('color_map', 'normal_map'):
            texture = getattr(material, name)
            if texture is not None:
                key = id(texture)
                if key not in snapshots:
                    pixels = texture._validated_pixels()
                    snapshots[key] = Texture(np.frombuffer(pixels.tobytes(order='C'), np.uint8).reshape(pixels.shape))
                maps[name] = snapshots[key]
        materials.append(replace(material, color_map=maps.get('color_map'), normal_map=maps.get('normal_map')))
    plate = replace(plate, materials=tuple(materials))
    printed = [material.print for material in plate.materials if material.print is not None]
    inputs = _render_inputs(engine, fonts, printed=bool(printed))
    textures = {texture.sha256: texture for texture in snapshots.values()}
    inputs = replace(inputs, textures=tuple(textures.items()))
    prints = {print_name(item): _print_document(item, inputs.font) for item in printed if inputs.font is not None}
    return inputs, document(plate), prints


def _render_to(
    plate: Plate, out: Path, inputs: _RenderInputs, folder: Path, source: bytes, prints: dict[str, bytes]
) -> Path:
    with tempfile.TemporaryDirectory(dir=folder) as work:
        root = Path(work)
        _lay_out(plate, root, inputs, folder, prints)
        document_ = root / 'plate.scene.xml'
        _private_bytes(document_, source)
        tmp = root / 'plate.png'
        _engine_render(inputs.engine, document_, tmp)
        inputs.check_engine()
        return _keep(tmp, out)


def verify(plate: Plate, *, engine: Path, cache: Path, fonts: Path) -> str:
    """Render ``plate`` again beside its cached file and refuse any difference: returns the sha256 of its pixels."""
    inputs, source, prints = _prepare(plate, engine, fonts)
    folder = inputs.folder(cache)
    kept = folder / f'{inputs.key("plate", source, tuple(prints.values()))}.png'
    if not kept.exists():
        _render_to(plate, kept, inputs, folder, source, prints)
    with tempfile.TemporaryDirectory(dir=folder) as work:
        again = _render_to(plate, Path(work) / 'again.png', inputs, folder, source, prints)
        first, second = pixels(kept), pixels(again)
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


def _png_bytes(rgba: np.ndarray) -> bytes:
    """The canonical RGBA8 encoding shared by plate files and bounded composition workers."""
    height, width = rgba.shape[:2]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    rows = b"".join(b"\0" + row.tobytes() for row in rgba.astype(np.uint8))
    body = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", body) + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b"")


def write_png(path: Path, rgba: np.ndarray) -> Path:
    """``rgba`` as an 8-bit PNG, the same bytes for the same pixels, mode 600."""
    data = _png_bytes(rgba)
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
