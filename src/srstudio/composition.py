"""Strict composition contracts, immutable preflight and verified vector emission.

Scene input is separate from host-owned asset bindings. Preflight validates the
declared manifest without executing builders, inspecting a cache or rendering.
Its costs are conservative declared bounds, not measured renderer RSS or timing.
Vector preparation checks actual payloads; emission compiles supported features
into a self-contained scene and atomically publishes it without rendering.
plate_view resolves perspective plate coordinates and shared lights. prepare_plate
verifies static geometry and texture pixels and produces a closed document/resource bundle
in a bounded worker. compile_bundle and emit_bundle combine verified vectors and
static plates with bounded rendering, verified caching and atomic publication.
Printed labels retain immutable recipes/font bytes and share the plate render budget.
Static proxies share the camera/lights and convert verified light/ID passes in
a bounded worker. RasterSequence verifies and emits held geometry/appearance
snapshots on explicit source clocks. ``scene_motion`` samples camera, light and
parent tracks into static validated plans; animated bundle emission and aggregate
motion render budgets remain unsupported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ._composition_plate_view import PlateView
    from .clay import Mesh
    from .plates import Material, Print, Texture
    from .proxy import Recipe

from .errors import SrstudioError

SCHEMA: Literal['srstudio.scene-plan/1.0.0'] = 'srstudio.scene-plan/1.0.0'
MAX_INPUT_BYTES = 1_048_576
MAX_LAYERS = 256
MAX_RECORD_ITEMS = 1024
MAX_GRAPH_ITEMS = 32768


class CompositionError(SrstudioError, ValueError):
    """An invalid, unsupported or over-budget composition request."""


def _fail(path: str, actual: object, expected: object, code: str = 'composition.input') -> CompositionError:
    return CompositionError(
        f'{path}: expected {expected}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Repair the named field using declared asset capabilities, explicit clocks and finite budgets.',
    )


@dataclass(frozen=True)
class _Record:
    def __post_init__(self) -> None:
        from ._composition_parse import validate_record

        validate_record(self)


@dataclass(frozen=True)
class StylePin(_Record):
    name: str
    revision: str


@dataclass(frozen=True)
class FrameRate(_Record):
    numerator: int = field(default=24, metadata={'minimum': 1, 'maximum': 120000})
    denominator: int = field(default=1, metadata={'minimum': 1, 'maximum': 10000})


@dataclass(frozen=True)
class CameraSpec(_Record):
    projection: Literal['orthographic', 'perspective'] = 'orthographic'
    position: tuple[float, float, float] = (0, 0, 10)
    target: tuple[float, float, float] = (0, 0, 0)
    origin: tuple[float, float] = (0, 0)
    scale: float = field(default=100, metadata={'minimum': 1e-6, 'maximum': 1e6})
    focal: float = field(default=10, metadata={'minimum': 1e-6, 'maximum': 1e6})
    near: float = field(default=0.01, metadata={'minimum': 1e-6, 'maximum': 1e6})


@dataclass(frozen=True)
class LightSpec(_Record):
    """World-space lights. Directional yaw/pitch rotate light travel from canonical +Z.

    Positive yaw turns toward +X; positive pitch turns toward -Y. Positions and
    area radii use the scene world unit; light intensities are backend power values.
    """

    id: str
    kind: Literal['ambient', 'directional', 'sphere-area']
    color: str
    intensity: float = field(metadata={'minimum': 0, 'maximum': 1e6})
    position: tuple[float, float, float] = (0, 0, 0)
    radius: float = field(default=0, metadata={'minimum': 0, 'maximum': 1e6})
    yaw: float = field(default=0, metadata={'minimum': -360, 'maximum': 360})
    pitch: float = field(default=0, metadata={'minimum': -90, 'maximum': 90})


@dataclass(frozen=True)
class LightRig(_Record):
    mode: Literal['flat', 'lit']
    lights: tuple[LightSpec, ...] = ()


@dataclass(frozen=True)
class Transform(_Record):
    """Source units into world units: uniform scale, XYZ rotations in degrees, then translation."""

    translation: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)
    scale: float = field(default=1, metadata={'minimum': 1e-6, 'maximum': 1e6})


@dataclass(frozen=True)
class TemporalPolicy(_Record):
    """Scene interval maps to source_start + (scene_time - start) * rate, exactly once."""

    start: float = field(metadata={'minimum': 0, 'maximum': 600})
    end: float = field(metadata={'minimum': 1e-6, 'maximum': 600})
    source_start: float = field(default=0, metadata={'minimum': 0, 'maximum': 600})
    rate: float = field(default=1, metadata={'minimum': 1e-6, 'maximum': 120})
    continuity: Literal['held', 'continuous', 'cut'] = 'held'
    state: str = ''


@dataclass(frozen=True)
class LayerSpec(_Record):
    id: str
    asset: str
    version: int = field(metadata={'minimum': 1, 'maximum': 1000000})
    temporal: TemporalPolicy
    role: Literal['picture', 'information'] = 'picture'
    space: Literal['world', 'screen'] = 'world'
    transform: Transform = field(default_factory=Transform)
    parent: str | None = None
    depth: Literal['ordered', 'split'] = 'ordered'
    passes: tuple[str, ...] = ('rgba',)
    intersects: tuple[str, ...] = ()
    surface_coordinates: Literal['local', 'screen'] = 'local'
    effects: tuple[str, ...] = ()
    shadow_receiver: str | None = None


@dataclass(frozen=True)
class ContactSpec(_Record):
    actor: str
    actor_anchor: str
    target: str
    target_anchor: str
    start: float = field(metadata={'minimum': 0, 'maximum': 600})
    end: float = field(metadata={'minimum': 1e-6, 'maximum': 600})
    tolerance: float = field(default=1e-5, metadata={'minimum': 0, 'maximum': 1e6})


@dataclass(frozen=True)
class RenderBudget(_Record):
    """Planning limits plus each worker's deadline and hard virtual-address-space cap.

    The memory cap includes worker runtime/libraries. Host intake/publication,
    GPU memory and independently invoked renderers are outside that process cap.
    """

    max_frames: int = field(default=2400, metadata={'minimum': 1, 'maximum': 100000})
    max_frame_pixels: int = field(default=16777216, metadata={'minimum': 1, 'maximum': 67108864})
    max_output_pixels: int = field(default=10_000_000_000, metadata={'minimum': 1, 'maximum': 1e12})
    max_nodes: int = field(default=500000, metadata={'minimum': 1, 'maximum': 1000000})
    max_new_plates: int = field(default=64, metadata={'minimum': 0, 'maximum': 10000})
    max_engine_invocations: int = field(default=128, metadata={'minimum': 0, 'maximum': 10000})
    max_samples: int = field(default=1_000_000_000, metadata={'minimum': 0, 'maximum': 1e12})
    max_bounces: int = field(default=8, metadata={'minimum': 0, 'maximum': 64})
    max_contact_samples: int = field(default=20000, metadata={'minimum': 0, 'maximum': 1000000})
    max_memory_bytes: int = field(default=8 * 1024**3, metadata={'minimum': 1, 'maximum': 1024**4})
    timeout: float = field(default=60, metadata={'minimum': 1e-6, 'maximum': 600})


@dataclass(frozen=True)
class ScenePlan(_Record):
    style: StylePin
    width: int = field(metadata={'minimum': 2, 'maximum': 8192})
    height: int = field(metadata={'minimum': 2, 'maximum': 8192})
    fps: FrameRate
    duration: float = field(metadata={'minimum': 1e-6, 'maximum': 600})
    seed: int = field(metadata={'minimum': 0, 'maximum': 2**32 - 1})
    world_unit: Literal['meter', 'centimeter', 'canonical-arm']
    camera: CameraSpec
    lights: LightRig
    layers: tuple[LayerSpec, ...]
    budget: RenderBudget
    contacts: tuple[ContactSpec, ...] = ()
    schema: Literal['srstudio.scene-plan/1.0.0'] = SCHEMA


@dataclass(frozen=True)
class Bounds(_Record):
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]


@dataclass(frozen=True)
class AnchorKey(_Record):
    time: float = field(metadata={'minimum': 0, 'maximum': 600})
    position: tuple[float, float, float]


@dataclass(frozen=True)
class Anchor(_Record):
    """An authored source-space anchor, static or piecewise linear with endpoint holds."""

    name: str
    position: tuple[float, float, float]
    keys: tuple[AnchorKey, ...] = ()


@dataclass(frozen=True)
class PlateWork(_Record):
    """One source-content job bound. Preflight also scopes it by resolved view/pose.

    Shared source keys must have identical work declarations. Different world
    placements require distinct cold renders even when their source is shared.
    """

    key: str
    width: int = field(metadata={'minimum': 1, 'maximum': 8192})
    height: int = field(metadata={'minimum': 1, 'maximum': 8192})
    samples: int = field(metadata={'minimum': 1, 'maximum': 4096})
    bounces: int = field(metadata={'minimum': 0, 'maximum': 64})
    engine_invocations: int = field(metadata={'minimum': 1, 'maximum': 10000})
    memory_bytes: int = field(metadata={'minimum': 1, 'maximum': 1024**4})


@dataclass(frozen=True)
class AssetBinding(_Record):
    """Host-authored asset facts; these are not accepted inside agent scene JSON.

    Bounds and anchors use source units; LayerSpec.transform.scale converts them
    to the scene world unit. Approval is resolved from the part table, never a
    caller-supplied boolean. Work declarations are bounds to enforce at emission.
    """

    id: str
    part: str
    version: int = field(metadata={'minimum': 1, 'maximum': 1000000})
    backend: Literal['vector', 'plates', 'proxy']
    bounds: Bounds
    anchors: tuple[Anchor, ...] = ()
    nodes: int = field(default=1, metadata={'minimum': 1, 'maximum': 1000000})
    memory_bytes: int = field(default=1, metadata={'minimum': 1, 'maximum': 1024**4})
    duration: float | None = None
    plates: tuple[PlateWork, ...] = ()


@dataclass(frozen=True)
class CostEstimate(_Record):
    frames: int
    frame_pixels: int
    output_pixels: int
    nodes: int
    unique_plates: int
    engine_invocations: int
    samples: int
    bounces: int
    memory_bytes: int
    contact_samples: int


@dataclass(frozen=True)
class ValidatedScenePlan(_Record):
    spec: ScenePlan
    bindings: tuple[AssetBinding, ...]
    cost: CostEstimate
    digest: str
    contacts_checked: int


def style_revision(name: str) -> str:
    """Content revision of an existing library style's declared settings; does not approve a new look."""
    from ._composition_preflight import style_revision as resolve

    return resolve(name)


def parse_scene(value: str | dict) -> ScenePlan:
    """Parse bounded strict JSON into deeply immutable records; reject unknown and duplicate fields."""
    from ._composition_parse import parse_scene as parse

    return parse(value)


def preflight(spec: ScenePlan, bindings: tuple[AssetBinding, ...]) -> ValidatedScenePlan:
    """Validate the complete declared composition without executing a builder or touching scene/cache state."""
    from ._composition_preflight import preflight as validate

    return validate(spec, bindings)


def plate_view(plan: ValidatedScenePlan, layer: str, *, meters_per_unit: float | None = None) -> PlateView:
    """Resolve one perspective world layer to a plate camera, lights and source transform.

    The returned image offset already includes projection. Composite that plate
    in screen space without the layer transform. Canonical-arm scenes require
    an authored meters_per_unit; metric units cannot be overridden. This adapter
    does not prepare geometry, render, approve a drawing or emit a composition.
    """
    from ._composition_plate_view import plate_view as resolve

    return resolve(plan, layer, meters_per_unit=meters_per_unit)


@dataclass(frozen=True)
class PreparedVector:
    """Verified immutable XML and measured envelope; the host owns drawing provenance."""

    binding: AssetBinding
    xml: bytes
    digest: str
    bounds: Bounds
    nodes: int


@dataclass(frozen=True)
class VectorSource:
    """Host-owned source bytes; preparation and compilation share one bounded worker."""

    id: str
    xml: bytes


@dataclass(frozen=True)
class PlateMaterial(_Record):
    id: str
    color: str
    roughness: float = field(default=0.68, metadata={'minimum': 0, 'maximum': 1})
    metallic: float = field(default=0, metadata={'minimum': 0, 'maximum': 1})
    emissive: str = ''
    color_map: str = ''
    normal_map: str = ''
    normal_scale: float = field(default=1.0, metadata={'minimum': 0, 'maximum': 16})
    sheen: str = ''
    subsurface: float = field(default=0.0, metadata={'minimum': 0, 'maximum': 1})
    print: str = ''


@dataclass(frozen=True)
class PlateMesh:
    """Owned little-endian float64 vertex/normal triples and int64 triangle triples.
    Optional UVs are little-endian float64 pairs, preserved without resampling.
    basis declares the input's Z direction: canonical is toward the viewer,
    clay is away. Binding bounds and anchors always use canonical source axes.
    """

    material: str
    vertices: bytes
    normals: bytes
    triangles: bytes
    basis: Literal['canonical', 'clay']
    uvs: bytes | None = None


@dataclass(frozen=True)
class PlateTexture:
    """Owned row-major RGBA8 pixels; dimensions and contents participate in identity."""

    id: str
    width: int
    height: int
    pixels: bytes


@dataclass(frozen=True)
class PlatePrint:
    """Immutable typed label recipe and font bytes; license is supplied by the host.

    Preparation verifies the TrueType metadata and compiles the label in its
    bounded worker. Rendering occurs only while compiling a bundle.
    """

    id: str
    recipe: Print
    font: bytes
    license: str


@dataclass(frozen=True)
class PlateSource:
    id: str
    meshes: tuple[PlateMesh, ...]
    materials: tuple[PlateMaterial, ...]
    meters_per_unit: float | None = None
    textures: tuple[PlateTexture, ...] = ()
    prints: tuple[PlatePrint, ...] = ()


@dataclass(frozen=True)
class PlateResource:
    name: str
    data: bytes


@dataclass(frozen=True)
class PreparedPlate:
    """Verified static plate and closed mesh, texture, label and font resources for one scene placement."""

    binding: AssetBinding
    source: PlateSource
    layer: str
    plan_digest: str
    source_digest: str
    xml: bytes
    resources: tuple[PlateResource, ...]
    bounds: Bounds
    nodes: int
    width: int
    height: int
    offset: tuple[float, float]
    digest: str


def plate_mesh(mesh: Mesh, *, basis: Literal['canonical', 'clay']) -> PlateMesh:
    """Snapshot bounded mesh arrays into immutable buffers; preparation verifies their semantics."""
    from ._composition_plate import snapshot

    return snapshot(mesh, basis=basis)


def plate_texture(id: str, texture: Texture) -> PlateTexture:
    """Snapshot bounded uint8 RGBA pixels without rendering or reading a file."""
    from ._composition_texture import snapshot

    return snapshot(id, texture)


def plate_source(
    id: str,
    meshes: tuple[Mesh, ...],
    materials: tuple[Material, ...],
    *,
    basis: Literal['canonical', 'clay'],
    meters_per_unit: float | None = None,
    print_font: bytes | None = None,
    print_license: str | None = None,
) -> PlateSource:
    """Snapshot existing geometry and materials, deduplicating pixel maps without losing authored fields.

    Printed-label recipes require explicit immutable TrueType font bytes and
    their license. prepare_plate verifies and compiles closed resources in a
    bounded worker; compile_bundle renders labels under the shared budget.
    """
    from ._composition_texture import snapshot_source

    return snapshot_source(
        id,
        meshes,
        materials,
        basis=basis,
        meters_per_unit=meters_per_unit,
        print_font=print_font,
        print_license=print_license,
    )


def plate_source_digest(source: PlateSource) -> str:
    """Identity for PlateWork.key, including geometry, maps, label recipes/fonts and physical scale."""
    from ._composition_plate_wire import source_digest

    return source_digest(source)


def prepare_plate(plan: ValidatedScenePlan, layer: str, source: PlateSource) -> PreparedPlate:
    """Verify static plate geometry, work and resources in a bounded worker, without rendering."""
    from ._composition_plate_runtime import prepare_plate as prepare

    return prepare(plan, layer, source)


@dataclass(frozen=True)
class ProxyPart(_Record):
    name: str
    tones: tuple[str, str, str, str]
    roughness: float = field(default=0.6, metadata={'minimum': 0, 'maximum': 1})


@dataclass(frozen=True)
class ProxyInk(_Record):
    colour: str = '#26303a'
    weight: float = field(default=0.8, metadata={'minimum': 0, 'maximum': 1024})
    grain: float = field(default=0.2, metadata={'minimum': 0, 'maximum': 1024})
    shade: float = field(default=0.5, metadata={'minimum': 0, 'maximum': 1024})
    least: float = field(default=0.6, metadata={'minimum': 0, 'maximum': 1024})
    most: float = field(default=2.0, metadata={'minimum': 0, 'maximum': 1024})


@dataclass(frozen=True)
class ProxyRecipe(_Record):
    """Immutable conversion controls. Illumination belongs to ScenePlan.lights."""

    parts: tuple[ProxyPart, ...]
    quiet: tuple[tuple[str, ...], ...] = ()
    behind: tuple[str, ...] = ()
    under: tuple[str, ...] = ()
    ink: ProxyInk = ProxyInk()
    thresholds: tuple[float, float, float] = (0.365, 0.475, 0.565)
    soft_edge: float = field(default=0.07, metadata={'minimum': 0, 'maximum': 1})
    oversample: int = field(default=2, metadata={'minimum': 1, 'maximum': 4})
    grain_seed: int = field(default=7, metadata={'minimum': 0, 'maximum': 2**53})


@dataclass(frozen=True)
class ProxySource:
    id: str
    meshes: tuple[PlateMesh, ...]
    recipe: ProxyRecipe
    meters_per_unit: float | None = None


@dataclass(frozen=True)
class PreparedProxy:
    binding: AssetBinding
    source: ProxySource
    layer: str
    plan_digest: str
    passes: tuple[PreparedPlate, ...]
    digest: str


@dataclass(frozen=True)
class RasterFrame:
    """An owned source snapshot held from this source time until the next snapshot."""

    time: float
    source: PlateSource | ProxySource


@dataclass(frozen=True)
class RasterSequence:
    """A bounded baked timeline. Frames begin at zero; the last holds until duration."""

    id: str
    duration: float
    frames: tuple[RasterFrame, ...]


@dataclass(frozen=True)
class RasterSpan(_Record):
    sample: int = field(metadata={'minimum': 0, 'maximum': MAX_RECORD_ITEMS - 1})
    start: float = field(metadata={'minimum': 0, 'maximum': 600})
    end: float = field(metadata={'minimum': 0, 'maximum': 600})


@dataclass(frozen=True)
class PreparedRasterFrame:
    time: float
    asset: PreparedPlate | PreparedProxy


@dataclass(frozen=True)
class PreparedRasterSequence:
    binding: AssetBinding
    source: RasterSequence
    layer: str
    plan_digest: str
    frames: tuple[PreparedRasterFrame, ...]
    digest: str


def proxy_source(
    id: str,
    meshes: tuple[Mesh, ...],
    recipe: Recipe,
    *,
    basis: Literal['canonical', 'clay'],
    lighting: Literal['scene'],
    meters_per_unit: float | None = None,
) -> ProxySource:
    """Snapshot a proxy recipe/geometry, explicitly replacing its lights with scene lights."""
    from ._composition_proxy import snapshot

    return snapshot(id, meshes, recipe, basis=basis, lighting=lighting, meters_per_unit=meters_per_unit)


def proxy_source_digest(source: ProxySource) -> str:
    """Full source identity including conversion controls; raw render jobs have separate keys."""
    from ._composition_proxy import source_digest

    return source_digest(source)


def proxy_jobs(source: ProxySource, *, width: int, height: int, memory_bytes: int) -> tuple[PlateWork, ...]:
    """Declare unique light/ID jobs from final view bounds; oversampling is applied once."""
    from ._composition_proxy import jobs

    return jobs(source, width=width, height=height, memory_bytes=memory_bytes)


def prepare_proxy(plan: ValidatedScenePlan, layer: str, source: ProxySource) -> PreparedProxy:
    """Verify a static proxy for one explicit rgba/back/front/under layer, without rendering."""
    from ._composition_proxy_runtime import prepare_proxy as prepare

    return prepare(plan, layer, source)


def raster_sequence_digest(source: RasterSequence) -> str:
    """Identity of all held snapshots, their times and the complete source duration."""
    from ._composition_sequence import source_digest

    return source_digest(source)


def raster_jobs(source: RasterSequence, *, width: int, height: int, memory_bytes: int) -> tuple[PlateWork, ...]:
    """Declare unique raw jobs for the entire timeline, including proxy passes and labels."""
    from ._composition_sequence import jobs

    return jobs(source, width=width, height=height, memory_bytes=memory_bytes)


def raster_schedule(plan: ValidatedScenePlan, layer: str, source: RasterSequence) -> tuple[RasterSpan, ...]:
    """Map source snapshots into half-open scene intervals, applying the clip clock once."""
    from ._composition_sequence import schedule

    return schedule(plan, layer, source)


def prepare_raster_sequence(plan: ValidatedScenePlan, layer: str, source: RasterSequence) -> PreparedRasterSequence:
    """Verify every plate/proxy snapshot in one bounded worker without rendering."""
    from ._composition_sequence_runtime import prepare_sequence

    return prepare_sequence(plan, layer, source)


@dataclass(frozen=True)
class CompiledScene:
    """A self-contained scene, its content identity and the manifest it implements."""

    xml: bytes
    digest: str
    plan_digest: str
    nodes: int


def prepare_vector(binding: AssetBinding, xml: bytes, *, budget: RenderBudget | None = None) -> PreparedVector:
    """Verify a host-prepared vector under a process memory cap and preemptive deadline."""
    from ._composition_runtime import prepare_vector as prepare

    return prepare(binding, xml, budget=budget)


def compile_scene(plan: ValidatedScenePlan, assets: tuple[PreparedVector | VectorSource, ...]) -> CompiledScene:
    """Verify and compile in a bounded worker; source bytes avoid a separate preparation invocation."""
    from ._composition_runtime import compile_scene as compile_

    return compile_(plan, assets)


def emit_scene(
    plan: ValidatedScenePlan,
    assets: tuple[PreparedVector | VectorSource, ...],
    output: Path,
    *,
    overwrite: bool = False,
) -> CompiledScene:
    """Compile in memory and publish one complete private scene file with an atomic installation."""
    from ._composition_emit import emit_scene as emit

    return emit(plan, assets, output, overwrite=overwrite)


@dataclass(frozen=True)
class BundleResource:
    name: str
    data: bytes


@dataclass(frozen=True)
class BundleWork:
    new_plates: int
    cache_hits: int
    engine_invocations: int


@dataclass(frozen=True)
class CompiledBundle:
    """A complete portable scene and its immutable PNG resources; work counts unique render jobs."""

    xml: bytes
    resources: tuple[BundleResource, ...]
    digest: str
    plan_digest: str
    nodes: int
    work: BundleWork


def compile_bundle(
    plan: ValidatedScenePlan,
    assets: tuple[PreparedVector | VectorSource | PreparedPlate | PreparedProxy | PreparedRasterSequence, ...],
    *,
    engine: Path,
    cache: Path,
) -> CompiledBundle:
    """Reverify all inputs, render bounded static plates and compile a portable mixed scene.

    Valid completed cache entries may survive a later runtime failure. Invalid
    input is refused before cache mutation. No retries are implicit.
    """
    from ._composition_bundle import compile_bundle as compile_

    return compile_(plan, assets, engine=engine, cache=cache)


def emit_bundle(
    plan: ValidatedScenePlan,
    assets: tuple[PreparedVector | VectorSource | PreparedPlate | PreparedProxy | PreparedRasterSequence, ...],
    output: Path,
    *,
    engine: Path,
    cache: Path,
) -> CompiledBundle:
    """Publish scene.xml and all PNGs as one new private directory; existing paths are refused.

    Atomic non-replacing directory publication requires Linux renameat2 support.
    """
    from ._composition_bundle import emit_bundle as emit

    return emit(plan, assets, output, engine=engine, cache=cache)
