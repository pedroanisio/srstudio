---
generated-by: OpenAI Codex (GPT-6)
---

# Validate and emit a composition

[Library README](../README.md) · [Drawing architecture](../DRAWING.md)

`srstudio.composition` validates a scene manifest against host-authored asset
bindings. It resolves approved part versions, coordinates, clocks, declared
contacts, supported passes and conservative work bounds. It returns immutable
records and a reproducible digest without invoking drawing builders, reading a
render cache or creating files.

`prepare_vector` verifies actual vector XML against a binding. `compile_scene`
combines verified payloads into a self-contained scene, and `emit_scene` publishes
that scene atomically. Public preparation and compilation run in workers with
hard address-space limits and preemptive deadlines. Plate renderer sessions also
enforce process limits and count retries; see [render sessions](authoring-benchmark.md#bound-a-plate-authoring-operation).
`prepare_plate` also verifies static mesh and texture payloads and prepares their
closed scene/resources in a bounded worker. `compile_bundle` and `emit_bundle`
combine verified vectors and static plates with bounded rendering and portable
image resources, including bounded printed labels. `prepare_proxy` adds static
light/part-ID conversion under the same camera, lighting and worker budgets.
`RasterSequence` adds baked geometry/appearance timelines under that shared
static view. Animated scene cameras, lights and parent transforms remain open
under SDK-P2-07.
A valid manifest alone is not a rendered scene,
approval of a new style, or proof of a host's declared geometry.

## Register a plate view

`plate_view(plan, layer_id)` derives a perspective plate camera and shared lights
from a revalidated plan. It resolves the complete parent transform and converts
canonical coordinates (+Z toward the reference viewer) to the plate backend's
centimeter-like units (+Z away). Metric scene units have fixed conversions;
`canonical-arm` requires an authored `meters_per_unit` argument.

```python
view = composition.plate_view(plan, "host")
engine_point = view.point((0.1, 0.2, 0.0))
engine_normal = view.direction((0.0, 0.0, 1.0))
# Build canonical source geometry using these mappings, then render a Plate
# with view.width, view.height, view.camera and view.lights.
image_x, image_y = view.offset
```

The image is already projected. Composite it at `view.offset` in screen space;
do not apply the layer or camera transform again. An off-center principal point
uses an enlarged render frame so shifting the image does not clip geometry at
the final frame's edges. The adapter checks that frame against dimension, pixel
and memory limits. `prepare_plate` checks the actual render-job dimensions and
work against the binding's declaration.

`point` consumes canonical source coordinates and applies all parents, uniform
scale, world-unit conversion and the Z reflection. `direction` rotates and
reflects normals without translation or scale. Converting triangle geometry
also requires reversing its winding (`view.reverses_winding`). Existing clay
meshes have a different source basis: explicitly convert their +Z-away vertices,
normals and winding to canonical source axes before using these mappings.
Shared lights stay in world space, independent of the layer's pose. Directional
yaw/pitch describe light travel from canonical +Z; positive yaw turns toward +X,
and positive pitch toward -Y. Area-light positions and radii convert with world
units; power and colors remain unchanged.

This adapter currently supports lit perspective world plate/proxy layers. It
refuses orthographic/screen/flat views, the engine's near-vertical up-axis switch,
field-of-view clamping and geometry outside the plate camera's clipping range.
The existing plate camera's ambient-occlusion defaults remain in effect. The
adapter does not verify mesh payloads, render, certify work declarations or emit
plate assets into a compiled scene. [Registration tests](../tests/test_composition_plate_view.py)
cover the mapping and a real-render landmark check; broader style and animated
adoption evidence remains separate.

## Prepare actual plate geometry

Snapshot host-owned `clay.Mesh` arrays with `plate_mesh(mesh, basis="clay")`, or
use `basis="canonical"` when the arrays already use +Z toward the viewer. The
basis declares orientation, not size: for centimeter-sized source coordinates
in a meter scene, use a layer scale of `0.01`. The snapshot owns immutable
little-endian float64 vertex/normal triples and int64 triangle triples. Subsequent
edits to the original arrays cannot change it.

```python
source = composition.PlateSource(
    "host",
    tuple(composition.plate_mesh(mesh, basis="clay") for mesh in meshes),
    (composition.PlateMaterial("skin", "#C88762"),),
)
source_key = composition.plate_source_digest(source)
# The host binding uses source_key as its PlateWork.key, declares canonical
# source bounds and budgets, and is validated with the complete ScenePlan.
prepared = composition.prepare_plate(plan, "host-layer", source)
```

Preparation checks finite vertices, matching unit normals, triangle indices,
material references, actual canonical bounds, the exact source-content key,
node count, overscan dimensions and the backend's sample/bounce settings. It
applies the shared view, transforms normals and reverses triangle winding as
required. The resulting schema-checked XML uses the scene seed and names only
the returned content-addressed mesh resources. It performs no filesystem/cache
writes and invokes no renderer. The worker has the plan's hard address-space
cap and parent-owned timeout.

`PreparedPlate` retains its immutable source, binding, layer/plan identities,
measured bounds, dimensions, offset, XML, resource bytes and a complete result
digest. Keeping the source allows later consumers to reverify its evidence.
This result is a preparation artifact; `compile_scene`/`emit_scene` still accept
vector assets only. Geometry provenance and approval remain host responsibilities:
checking numerical mesh constraints does not prove it is an approved drawing.

`PlateWork.key` identifies source content, including materials, coordinate basis
and physical scale. It is not a rendered-cache key. Preflight scopes jobs by
resolved placement, backend and passes: two placements of the same source need
two cold renders; identical placements can share one. A rendered artifact must
also bind the actual camera, lighting, renderer and other rendering inputs.

The preparation adapter accepts one static plate job per source, up to 128
meshes, 128 materials, 128 textures and 128 printed labels, with eight MiB of combined input buffers.
Prepared XML/resources have a separate eight MiB cap. Materials support `#RRGGBB`
base, emissive and sheen colors, roughness/metallic/subsurface values in `0..1`,
and normal-map strength in `0..16`. Printed labels require explicit font bytes
and license metadata. Proxy recipes and animated source bindings are refused. Source memory declarations
must cover eight times the input buffer bytes; the job must cover prepared
resource storage and its frame buffer. These storage checks complement the
hard process cap; they do not measure or guarantee renderer/GPU peak memory.

[Payload tests](../tests/test_composition_plates.py) exercise typed refusals,
mutable-input snapshots, malformed worker messages, kernel memory limits,
timeouts, placement accounting and a real render using only the prepared files.

## Preserve textured materials

Use the snapshot adapter with existing `clay.Mesh` and `plates.Material` values:

```python
source = composition.plate_source(
    "host", tuple(meshes), tuple(materials), basis="clay",
)
# Bind composition.plate_source_digest(source) as the PlateWork.key, preflight
# the complete manifest, then verify the source in its selected placement.
prepared = composition.prepare_plate(plan, "host-layer", source)
```

The adapter copies geometry, UVs and `plates.Texture` pixels into immutable bytes.
It preserves color maps, normal maps, their strength, sheen and subsurface values.
Shared pixel maps are deduplicated by both dimensions and contents. A
`Material.print` requires the font inputs described below. A material cannot
specify both a printed label and a color map.

For explicit records, `plate_texture("paint", texture)` creates a `PlateTexture`.
Put it in `PlateSource.textures` and name it with
`PlateMaterial(..., color_map="paint")` or `normal_map="paint"`. Every declared
texture must be referenced by a material, IDs must be unique, and every reference
must resolve. Texture records contain width, height and exact row-major RGBA8
bytes. Arrays must already be `uint8` with four channels; no implicit quantization
or alpha conversion occurs. Each dimension is in `1..8192`, subject to the
combined eight MiB raw-input cap.

Every textured mesh needs one finite float64 UV pair per vertex. UVs remain in
source surface coordinates through parent transforms and camera projection.
Repeated coordinates outside `0..1` are retained; the adapter neither clamps them
nor invents a mapping for an unwrapped mesh. The existing engine OBJ convention
and sampler determine orientation and wrapping. PNG encoding and OBJ generation
run inside the bounded preparation worker without filesystem writes.

Prepared resources use `textures/<PNG-sha256>.png` and `meshes/<OBJ-sha256>.obj`.
PNG identity includes its dimensions, so equal pixel bytes in differently shaped
images cannot alias. Source identity includes UVs, raw pixels, dimensions and
material fields. Untextured inputs using the original defaults retain their
existing source and prepared identities; extended sources use identity schema
`srstudio.plate-source/1.1.0` for textures and `1.2.0` for printed labels.
Renderer caches include the prepared resources, so a
changed map produces a new render job. Public bundle compilation reverifies the
original source and rejects forged prepared resources before rendering.

[Texture tests](../tests/test_composition_textures.py) cover ownership, coordinate
basis parity, repeated UVs, material preservation, closed resource limits, source
and cache identities, typed refusals, and a rendered color-map registration probe.
These checks establish material transport and rendering on the tested engine;
they do not approve a new character drawing or a texture-animation policy.

## Preserve printed labels

For materials with an existing `plates.Print`, supply the font's immutable bytes
and its license identifier explicitly:

```python
source = composition.plate_source(
    "host", tuple(meshes), tuple(materials), basis="clay",
    print_font=font_bytes, print_license="OFL-1.1",
)
```

The host owns the font selection and license declaration. The adapter performs
no download or filesystem read. `PlateSource.prints` holds immutable `PlatePrint`
records containing each exact `plates.Print` recipe, font bytes and license;
`PlateMaterial.print` names the record. Identical recipes and font inputs are
deduplicated. Every record must be referenced, every reference must resolve,
and every printed mesh must have authored UVs. Text uses `plates.PRINTABLE`.
Recipes allow at most 128 lines, 4096 characters per line and 32768 text bytes
in total. Dimensions are `2..8192`; all labels together are limited to eight MiB
of decoded RGBA pixels, independently of the source-buffer cap.

Preparation inspects the TrueType font's actual family, weight and upright style
inside the bounded worker, compiles and schema-checks each label scene, and
retains content-addressed `prints/<scene-sha256>.scene.xml` and
`fonts/<font-sha256>.ttf` resources. Source and prepared identities include the
recipe, font and license. Preparation does not invoke the renderer. Invalid
font metadata, ambiguous color maps and unsupported label inputs produce
`CompositionError` before cache or output mutation.

The source still has one `PlateWork` declaration. For `N` distinct labels, its
`engine_invocations` must cover `N + 1`, and its `samples` must cover
`plates.SAMPLES * (N + 1)`; the latter conservatively charges the same sample
bound for each label. Its width and height cover the maximum of the registered
plate view and every label. Node and memory bounds include compiled label
scenes and fonts. Existing global field caps still apply: a large label set can
exceed the sample or byte budget even when its count fits.

A cold bundle renders each unique label scene, validates its PNG dimensions,
CRC and bounded decompression, then renders the plate. All attempts consume
the per-source, plan and enclosing render-session limits. `new_plates` counts
completed plate jobs; `engine_invocations` includes their label attempts. Labels
are intermediate dependencies within the private render directory. Only a
fully verified plate enters the cache, and a warm plate needs no label render.
The portable bundle contains the final images, so it needs neither fonts nor
label recipes at playback. Changing font bytes or recipe content invalidates
the dependent plate cache.

[Print tests](../tests/test_composition_prints.py) exercise bounded input and wire
validation, font provenance, closed preparation, failure preservation, cache
invalidation, nested attempt limits and a real rendered UV label probe. This
establishes label transport; it does not certify arbitrary text legibility.

## Prepare a static proxy

`proxy_source` snapshots existing mesh arrays and a `proxy.Recipe`. Its required
`lighting="scene"` argument explicitly replaces that recipe's private lights with
the shared scene rig. Immutable `ProxyRecipe`, `ProxyPart` and `ProxyInk` records
also support direct host construction. No callable or file path crosses the
worker boundary.

```python
from srstudio import clay, proxy
from srstudio import composition as c

model = clay.Model()
model.box("body", (0, 0, 0), (0.2, 0.2, 0.2))
recipe = proxy.Recipe({"body": ("#102030", "#506070", "#90A0B0", "#D0E0F0")})
source = c.proxy_source(
    "host", tuple(model.meshes()), recipe, basis="clay", lighting="scene"
)
# Width/height bound the final registered view, including any principal-point
# overscan. proxy_jobs applies the recipe's oversampling exactly once.
jobs = c.proxy_jobs(source, width=64, height=64, memory_bytes=8 * 1024**2)
binding = c.AssetBinding(
    "host", "rafa", 1, "proxy", c.Bounds((-1, -1, -1), (1, 1, 1)),
    nodes=128, memory_bytes=32 * 1024**2, plates=jobs,
)
spec = c.ScenePlan(
    c.StylePin("toon", c.style_revision("toon")), 64, 64, c.FrameRate(), 1, 7,
    "meter", c.CameraSpec("perspective", (0, 0, 10), (0, 0, 0), (32, 32), 100, 10),
    c.LightRig("lit", (c.LightSpec("ambient", "ambient", "#FFFFFF", 1),)),
    (c.LayerSpec("host", "host", 1, c.TemporalPolicy(0, 1), passes=("rgba",)),),
    c.RenderBudget(timeout=120),
)
plan = c.preflight(spec, (binding,))
prepared = c.prepare_proxy(plan, "host", source)
```

This box demonstrates the host binding and preparation protocol; a valid binding
is not approval of new geometry or a new style. Pass `prepared` to
`compile_bundle` or `emit_bundle` alongside the other prepared placements.
Preparation validates the actual geometry and returns light/ID documents without
rendering. The light pass uses world-space scene lights; the semantic ID pass
uses black ambient illumination and deterministic emissive material IDs.

Each proxy layer selects exactly one pass:

| Pass | Image contents |
| --- | --- |
| `rgba` | Full converted model, including its normally visible under parts |
| `back` | Designated behind parts; under parts are excluded |
| `front` | Other visible parts; behind and under parts are excluded |
| `under` | A separate under-only render, including surfaces hidden by the full model |

Use separate layers with the same asset and pose to place supported plate/proxy
picture assets between `under`, `back` and `front`. Those layers share identical
raw render jobs. Vector information can be placed above all picture layers;
vector picture assets still require a shared-light adapter and are refused in
this lit workflow. A
recipe with under parts declares four jobs; otherwise it declares two. If the
under subset is the whole model, identical jobs are deduplicated. The planning
estimate may conservatively count separate selected passes; actual `BundleWork`
counts unique cold/warm raw jobs and real launch attempts. No depth or normal
pass, automatic intersecting-layer strategy or cross-layer shadow receiver is
implied.

`proxy_source_digest` includes palette, ink and grain controls. The `PlateWork`
keys returned by `proxy_jobs` identify only the raw geometry/material inputs.
Changing tones or grain can therefore reuse verified light/ID cache entries
while producing a new converted image. Changed geometry, roughness, view,
lighting or renderer bytes invalidate the affected raw renders. Conversion
runs again in the bounded worker on warm builds. Portable bundles contain only
the selected converted PNGs; intermediate light/ID images stay in the cache.

The immutable adapter supports 1–64 parts and oversampling 1–4. Mesh and recipe
inputs, combined prepared pass resources, conversion PNG inputs and final
bundle files each have an eight MiB cap. Raw dimensions must stay within 8192
and the plan's frame-pixel budget. For `P` raw pixels and `N` palette parts,
the binding's memory declaration must cover at least
`8 * source_bytes + P * (64 * N + 512)` bytes. This reserves the part-distance
tensor and conversion intermediates; it is not measured RSS. Job declarations
also cover the actual raw dimensions, samples, bounces and prepared storage.
Worker memory/deadline limits remain authoritative. Ink uses final image pixels;
premultiplied-alpha downsampling applies oversampling once. Tiny parts remain
subject to the existing proxy classifier's 3×3 opening.

[Proxy tests](../tests/test_composition_proxy.py) execute this recipe and check
shared projection, all four conversion results, content-sensitive cache reuse,
malformed inputs, forged evidence and real-engine part-ID registration.
Animation, temporal stability and style approval require the separate
[DRAWING acceptance study](../DRAWING.md#proof-and-acceptance-gates).

## Animate held raster snapshots

`RasterSequence` stores immutable `RasterFrame` snapshots on a finite source
clock. Each snapshot contains a complete `PlateSource` or `ProxySource`, so
geometry, materials, texture pixels, printed labels and proxy conversion controls
can change over time. Frames start at zero, strictly increase, and remain below
`duration`. Each is held until the next frame; the last holds until the source
ends. This is baked playback with explicit replacements, not mesh interpolation
or a promise of continuous motion.

```python
from srstudio import clay, composition as c, plates

def snapshot(x, color):
    model = clay.Model()
    model.box("skin", (x, 0, 0), (0.2, 0.2, 0.2))
    return c.plate_source(
        "host", tuple(model.meshes()), (plates.Material("skin", color),), basis="clay"
    )

first = snapshot(0, "#C88762")
second = snapshot(-0.12, "#00AAFF")
source = c.RasterSequence(
    "host", 2, (c.RasterFrame(0, first), c.RasterFrame(0.5, second), c.RasterFrame(1.5, first))
)
binding = c.AssetBinding(
    "host", "rafa", 1, "plates", c.Bounds((-1, -1, -1), (1, 1, 1)),
    nodes=256, memory_bytes=16 * 1024**2, duration=source.duration,
    plates=c.raster_jobs(source, width=64, height=64, memory_bytes=8 * 1024**2),
)
clock = c.TemporalPolicy(0.5, 1.375, source_start=0.25, rate=2)
spec = c.ScenePlan(
    c.StylePin("toon", c.style_revision("toon")), 64, 64, c.FrameRate(4), 2, 7,
    "meter", c.CameraSpec("perspective", (0, 0, 10), (0, 0, 0), (32, 32), 100, 10),
    c.LightRig("lit", (c.LightSpec("ambient", "ambient", "#FFFFFF", 1),)),
    (c.LayerSpec("host", "host", 1, clock),), c.RenderBudget(timeout=120),
)
plan = c.preflight(spec, (binding,))
schedule = c.raster_schedule(plan, "host", source)
prepared = c.prepare_raster_sequence(plan, "host", source)
```

This example illustrates the protocol using a box; its host binding does not
approve new geometry as a character. Pass `prepared` to `compile_bundle` or
`emit_bundle`. The schedule contains source sample indices and half-open scene
intervals: `[0.5, 0.625)`, `[0.625, 1.125)` and `[1.125, 1.375)`. At an exact
boundary only the new snapshot is visible. Source offsets and playback rates
are applied once. Decimal-to-rational clock arithmetic avoids accumulating
successive interval errors, and intervals that collapse at scene-time floating
precision are refused.

To use proxies, supply `ProxySource` snapshots, set the binding backend to
`"proxy"`, and select one supported pass in the layer. Every snapshot must
support that pass. A sequence keeps one source ID, backend, physical unit scale
and proxy oversampling factor. The shared scene camera, lights and parent
transforms remain static; snapshots can contain baked object motion in source
coordinates. Host code samples its motion explicitly before snapshotting. No
builder, mutable array, live recipe mapping or callback crosses the worker
boundary.

`raster_jobs` declares unique raw jobs for the complete source. Identical
geometry/appearance snapshots share render work; proxy palette/grain-only
changes can reuse raw light/ID images and still get converted again. Print
jobs include their label attempts. `raster_sequence_digest` includes every
source snapshot, timestamp and the finite duration. Job dimensions bound the
registered view including overscan, and proxy oversampling applies once.

Preparation verifies every snapshot, including ones outside the selected clip,
under the original validated plan and binding. Animated anchors, declared
contacts, source duration and shared budgets retain their original identities.
Rendered geometry does not independently certify a host-declared anchor.
Emission renders only snapshots whose held intervals intersect the clip and
reuses verified cache entries across retimed cuts and out-of-order builds.
Repeated output images are sent once per sequence with checked image references.
The portable scene stores explicit visibility intervals and selected PNGs.

A source contains at most 1024 snapshots. Combined source buffers and prepared
resources each stay within eight MiB, even when a snapshot repeats. The binding's
node declaration covers all prepared snapshots; memory covers at least eight
times the complete source buffers and prepared resources, plus each proxy's
conversion requirements. Worker deadlines/address-space caps, render attempts,
pixel/sample limits and final bundle/IPC byte caps remain enforced. A failed
snapshot leaves the cache untouched; completed render entries may survive a
later runtime failure, but publication never installs a partial bundle.

The [timeline tests](../tests/test_composition_sequences.py) cover source clocks,
held boundaries, invalid unseen snapshots, closed IPC, animated anchor records,
cold/warm work and real-rendered plate/proxy motion. Smoothness, moving scene
cameras, shared-light vector picture adapters, receivers and the complete
animated [drawing acceptance study](../DRAWING.md#proof-and-acceptance-gates)
remain separate requirements.

## Render and publish a mixed bundle

```python
from pathlib import Path

bundle = composition.emit_bundle(
    plan,
    (prepared, composition.VectorSource("overlay", overlay_xml)),
    Path("output/shot"),
    engine=Path("/path/to/scene-render"),
    cache=Path("cache/plates"),
)
# output/shot/scene.xml and image-<sha256>.png travel together.
print(bundle.work.new_plates, bundle.work.cache_hits, bundle.work.engine_invocations)
```

Supply one `PreparedPlate` per plate layer and one `VectorSource` or
`PreparedVector` per vector binding. All sources and their evidence are reverified
before cache mutation or renderer invocation. `compile_bundle` returns the same
immutable XML/resources without publishing an output directory; it can populate
the render cache.

Each unique render job binds the prepared XML, mesh resources and actual renderer
bytes. Identical jobs share one render, including repeated static placements in
different time windows. Warm entries must pass record, content, dimension, CRC and
bounded PNG decompression checks; corruption is refused without repair or retry.
Changing renderer bytes creates a different cache identity. Valid completed cache
entries can remain after a later job or final publication fails.

Rendering inherits every enclosing `plates.render_session` limit and also enforces
the plan's invocation, address-space and per-invocation timeout limits. Each file
written by the renderer has a 256 MiB kernel limit, allowing graphics-backend
scratch/mapped files larger than the final PNG. This is a per-file limit,
not an aggregate disk quota. PNG verification and final scene assembly execute
in bounded workers. Complete bundle files are limited to eight MiB; the bounded
wire protocol can refuse large repeated inputs before assembly.

Plate images already contain the parent/camera transform and are placed at the
registered screen offset exactly once. Vector layers retain their authored
geometry, clocks and stacking order. Static plate visibility follows the layer's
start/end interval; this adapter supports static textures but does not supply animated geometry or texture changes.

`emit_bundle` publishes all files as one new directory using Linux
`renameat2(RENAME_NOREPLACE)`. Existing destinations, including empty directories,
are refused. Output and cache directories must not overlap. New directories use
mode `700`, files use `600`. Publication requires filesystem support for this
operation; no partial-output fallback is used. Atomic visibility does not promise
recovery after power loss.

The [bundle tests](../tests/test_composition_bundles.py) exercise cold/warm work,
renderer failures, cache integrity, placement and real mixed-scene rendering.
These numeric fixtures do not establish drawing approval or animated style quality.

## Start with a real drawing

Run the [pinned paper example](../examples/composition_preflight.py):

```sh
python examples/composition_preflight.py
python examples/composition_preflight.py --output generated/papers.scene.xml
```

The example prepares approved `papers` version 1 using the existing SDK, checks
its scene, counts its nodes, and supplies authored source bounds and a working
memory allowance. Its test checks the real drawing's control points and strokes
against those bounds. The drawing origin is a coordinate anchor; it does not
claim a hand grip or collision surface. One source drawing unit becomes 0.001
meters through the layer's explicit scale.

The optional output command verifies the payload and emits a scene. An existing
destination requires `--overwrite`; replacement publishes the complete file in
one operation. Rendering remains a separate engine operation.

## Parse and inspect

```python
import json
from dataclasses import asdict
from srstudio.composition import parse_scene, preflight

# spec is a ScenePlan; bindings is an immutable tuple of AssetBinding records
request = parse_scene(json.dumps(asdict(spec)))
checked = preflight(request, bindings)
print(checked.digest, checked.cost.frames, checked.cost.engine_invocations)
```

## Verify and emit actual vectors

The host supplies UTF-8 scene bytes for each used binding. Preparation verifies
schema validity, closed resources, actual node count, declared memory allowance,
and a conservative envelope for every supported animation pose. The payload hash
binds those checks to the exact bytes. Compilation reruns preflight and payload
validation, so editing a frozen record through `dataclasses.replace` cannot reuse
stale costs, approvals or geometry evidence.

```python
from pathlib import Path
from srstudio.composition import VectorSource, compile_scene, emit_scene

# checked is the preflight result; source_bytes is the host's id-to-bytes map.
sources = tuple(VectorSource(b.id, source_bytes[b.id]) for b in checked.bindings)
compiled = compile_scene(checked, sources)  # immutable XML, digest, actual nodes
emit_scene(checked, sources, Path("generated/scene.xml"))
```

`VectorSource` sends host-owned bytes through preparation and compilation in one
worker. To inspect measured geometry separately, call
`prepare_vector(binding, xml, budget=checked.spec.budget)`; it returns a frozen
`PreparedVector`, also accepted by compilation. Omitting that preparation budget
uses the default `RenderBudget`. Each public call has its own worker lifetime;
preparing every source separately adds worker startup costs. Neither input form
executes an arbitrary drawing callback in the worker.

The vector adapter supports nested groups, paths, rectangles, rounded rectangles,
ellipses, local linear/radial gradients, and numeric transform/opacity or boolean
visibility keys. Scalar lengths are explicit source units. Keys use local or
composition seconds, held endpoint extrapolation, and non-overshooting linear,
hold, sine, quadratic, cubic, quartic, quintic, exponential or circular easing.
Animated rotations use a conservative full-circle envelope; correlated tracks
can therefore need more generous declared bounds than a sampled screenshot.

External assets, text/fonts, includes, instances, expressions, deformation,
effects, overshooting curves and unsupported shape kinds fail explicitly. The
adapter does not execute a builder or render while discovering those features.
The host remains responsible for payload provenance and authored anchor meaning:
validating XML cannot prove that it was made by a particular approved builder.
The worked example obtains its drawing directly from `parts.drawing('papers', 1)`.

Each placement scopes its IDs and paint references. A parent transform and the
camera are applied once; the emitted layer clock maps to source seconds without
moving source keys. Screen-space information retains its pixel coordinates.
The output is one self-contained file, so atomic installation cannot expose an
XML file whose companion resources are still being written. New files and
directories are private. An existing destination is preserved unless explicit
`overwrite=True` requests atomic replacement; validation and write failures
preserve the old destination.

Payloads and expanded output have an eight MiB cap, finite node limits and a
64-element nesting limit. Repeated placements include their copy/serialization
allowance before expanded trees are allocated. The host rejects known node and
expansion budget failures before launching work. The worker repeats semantic
validation, verifies actual payloads and compiles the result. Input and result
messages use closed, bounded JSON with base64 bytes; executable Python objects
are never deserialized.

## Runtime limits

`RenderBudget.max_memory_bytes` sets the worker's hard `RLIMIT_AS` limit before
SDK imports. It includes the interpreter, libraries, mappings and allocation
overhead, so the declared scene-memory estimate is not a sufficient worker
budget by itself. This is a per-process virtual-address-space cap, not a peak-RSS
estimate or GPU-memory limit. An inherited lower process limit is preserved.
The host application retains its own limits. Native math thread counts are one
inside the worker; the host environment is unchanged.

`RenderBudget.timeout` bounds each worker invocation, including startup, input
transfer, verification and compilation. The parent stops the entire worker
process group on timeout or excessive output, including descendants whose leader
has exited. Input, stdout and stderr have byte caps; a worker cannot exhaust host
memory by printing indefinitely or stall input transfer beyond the deadline.
Workers do not write scene outputs. The parent checks the complete reply's schema,
manifest/content hashes and node count before atomic publication.

POSIX process groups and kernel address-space limits are required; unsupported
platforms refuse rather than running unbounded. The installed SDK and approval
records must be available in the worker. In-process monkeypatches or dynamically
registered host-only builders are not transferred. Host drawing generation,
bounded manifest intake and final filesystem publication are outside the worker.
This execution boundary is not a sandbox for hostile Python programs.

The vector compiler makes no engine calls. Rendering its output independently
does not inherit these budgets. Static plate/proxy bundle rendering does inherit
the plan limits; independently rendered scene playback needs its own session. Timeout and memory-allocation failures expose budget paths;
other worker startup, exit or protocol failures have explicit worker codes.
There are no automatic retries. Typed SDK causes, including part-version errors,
survive the worker boundary through a closed diagnostic protocol.

Scene JSON uses schema `srstudio.scene-plan/1.0.0`. Unknown fields, duplicate JSON
keys, booleans in numeric fields, nonfinite numbers and excessive input graphs
are refused. Records are frozen, and nested collections are tuples. The JSON
boundary is limited to one MiB; direct dictionaries also have total string,
collection, nesting and graph limits.

`AssetBinding` is a host-side declaration, separate from agent scene JSON. The
host owns the facts about prepared geometry, anchors, source duration, work and
backend. Preflight checks consistency and supported capabilities; it does not
derive those facts from a part name. A binding has a numbered part version,
resolved through `parts.pin`, so a replaced or unapproved builder cannot borrow
the original approval metadata. A `StylePin` records the existing library
style's settings revision from `style_revision(name)`; it does not approve a
new style recipe.

## Coordinates and clocks

World coordinates use x right, y down and z toward the reference viewer. A
`Transform` applies uniform source-to-world scale, XYZ rotations in degrees,
then translation. Parent references compose that mapping once and must be
acyclic. A world camera owns the view and near plane. Vector source views must
remain frontal; declaring an off-axis pose cannot synthesize a new drawing.

Screen layers use drawing pixels and bypass the world camera. Information must
be screen-space vector geometry, above every picture layer, with no per-layer
finish. A parent frame must use the same coordinate space. Screen coordinates
cannot participate in world contacts.

`TemporalPolicy` maps an interval using
`source_start + (scene_time - start) * rate`. Source windows must fit the declared
source duration. A named state uses one pinned source asset. Adjacent continuous
windows must retain source time, rate and world placement; cuts are explicit.
No noise-channel or facial-transition behavior is inferred from these records.

Contacts compare authored world anchors over an explicit interval. Static
anchors and piecewise-linear source tracks are supported. The validator checks
the union of both tracks' key times and contact endpoints: between those times,
the difference is affine and its distance is bounded by the endpoints. Contact
sampling has a separate finite budget. This validates declared coordinate
agreement; it does not solve a skeleton or infer biomechanical validity.

## Costs and unsupported requests

| Estimate | Meaning |
| --- | --- |
| Frames and output pixels | Exact ceiling from decimal duration and rational fps |
| Nodes | Declared nodes per layer plus container allowance |
| Unique plates | Distinct content keys in used asset bindings, assuming a cold cache |
| Engine invocations | Sum of the distinct jobs' declared attempts |
| Samples and bounces | Pixel path samples summed across jobs; maximum bounce count |
| Memory bytes | Declared asset working storage, largest sequential job, two RGBA frame buffers and node allowance |
| Contact samples | Actual endpoint/key comparisons performed by manifest validation |

Work declarations sharing a content key must match. Input binding order does
not change the result, and unused bindings do not contribute work. Estimated
memory is a planning allowance, not measured process RSS. The separate hard
worker address-space cap also includes runtime overhead. Cache reuse can make
actual render work smaller; preflight does not inspect cache contents.

Cross-layer shadow receivers, split-pass intersections and per-layer finish
currently refuse with `composition.capability`. A lit scene refuses vector
picture assets without a shared-light adapter. Missing passes are never dropped.
These refusals keep unsupported emission behavior explicit while its adapters
are implemented.

Catch `CompositionError` and inspect `to_dict()` for `code`, `path`, `actual`,
`expected` and `remedy`. Version failures preserve the underlying part error as
their cause. Correct the named field before retrying; validation never mutates
the supplied manifest or binding records.
