---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
updated-by: Codex (OpenAI); Claude Opus 5.5 (claude-opus-5-5) in Claude Code
status: accepted
---

# Drawing architecture: a hybrid, layered kit

srstudio's drawing direction is a hybrid kit: each kind of element uses the method suited to it, with a shared lighting model and a finish owned by the style or show. Each style takes the layers its look needs, so a Collage reel stays paper and a Maps reel stays a map. This is the default for new work ([ADR 0091](docs/decisions/0091-hybrid-drawing-is-the-default.md)). Published reels stay frozen and approved drawings stay pinned. The rigid-object layer is built: `srstudio.proxy`, `srstudio.vehicle` and `srstudio.on_beat`, with [examples/car_vibe](examples/car_vibe/car_vibe_study.py) as the worked example. `forms` and `paint` remain proposed. [Composition preflight and vector emission](docs/composition-preflight.md) supplies typed records, read-only validation, verified vector payloads and atomic self-contained scene output. Vector preparation and compilation use bounded worker processes. Plate/proxy emission, renderer budget integration and the complete shared scene contracts below remain unfinished.

The kit addresses different needs without requiring every video to use every technique. A single 2D path does not encode a rigid object's unseen surfaces; independently drawn views can drift. Drawn characters already have shading primitives, but need a shared way to attach shading to moving forms and light. Environments need controlled depth and surface texture. Information has the opposite need: captions, cards and map lines must stay exact. A fixed view can remain entirely 2D; multi-view geometry becomes useful when its consistency justifies the rendering cost.

## Existing capabilities and remaining gaps

| Capability | Implementation evidence | Remaining work |
|---|---|---|
| Drawn form shading | [brush.py](src/srstudio/brush.py) supplies `crescent`, `Hand`, and `inked`; [Toon Inked](src/srstudio/toon_inked.py) uses a cheek crescent; [brush tests](tests/test_brush.py) check its geometry | Shared light, pose, and receiver bindings; reuse these primitives in `forms` |
| Modeled, lit plates | [plates.py](src/srstudio/plates.py), [clay.py](src/srstudio/clay.py), and [ADR 0068](docs/decisions/0068-rafa-clay-host-on-plates.md) describe cached path-traced plates, normal maps, measured rendering, and Rafa's approved look | [proxy.py](src/srstudio/proxy.py) converts a proxy to cel plates and layers for fixed views; moving cameras and turning objects are unproven |
| Finish and depth cues | [look.py](src/srstudio/look.py) supplies `grade`, `depth`, `pool`, and `fade` | `depth` is a blur group, not a shared depth buffer or camera; define ordering and receivers separately |
| Paint and effects | [Canvas](src/srstudio/canvas.py) wraps linear/radial gradients and generic effect application; the [schema](https://github.com/pedroanisio/scene-render/blob/af179e456d29f5bbc82c86187cccd620cf0e3124/schema/scene-render-1.1.xsd) also declares mesh/conic gradients and texture effects | Convenient paint wrappers and a measured animated style recipe |
| Effect rendering | [renderer tests](https://github.com/pedroanisio/scene-render/blob/af179e456d29f5bbc82c86187cccd620cf0e3124/crates/sr-gpu/tests/raster_effects/effects.rs) contain pixel checks for posterize, gradient-map, lighting, and outline | Existing tests do not establish the proposed combined aesthetic; run the proof against the exact srstudio and engine builds selected for adoption |

The schema establishes syntax, source code establishes implementation, and a passing render establishes behavior on a particular build. These are separate evidence levels. Videos render with engine 0.8.0, while the linked engine files come from a checkout at v0.9.0. The effect shader is identical at both tags; the schema and the effect tests differ, so a claim drawn from them holds for production only once it is checked at v0.8.0. The effects, the mesh and conic gradients, and the posterize, gradient-map, lighting and outline tests named above are all present at v0.8.0. No claim that all these features are untested, or unused by every video, is needed for this decision.

## The five layers

Rigid objects seen from more than one angle can use 3D proxies: vehicles, buildings, furniture, machines, products and props. An object seen from one angle can stay a drawing. A proxy is modeled in `srstudio.clay` and rendered through `srstudio.plates`, within its declared camera/view envelope. Its style conversion preserves the approved palette and marks: flat, inked bands in Toon, paper in Collage, vinyl in Gloss. Each changed camera or object pose can require a new plate; caching does not turn a continuous camera move into one render. `srstudio.proxy` holds the conversion, and a `Recipe` holds a style's numbers. `srstudio.vehicle` adds tyres and rims: a rim stays a vector drawing on the disc `View.disc` gives, so a turning wheel needs no new plate.

Characters stay on their style's rig: people, animals and creatures. The proposed `forms` module composes existing brush shading with rig anchors, shared lighting, and explicit shadow receivers. A rig declares supported views and poses; reusing its parametric parts does not synthesize an unseen back or profile. Form shading is opt-in per look, because a stick figure, a Soft blob and a traced Cel drawing are flat on purpose. Rafa stays on plates. Cross-surface shadows require the receiver representation described below before they can be promised.

Environments can use painted plates arranged in depth layers. The proposed `paint` module extends `Canvas` with mesh- and conic-gradient wrappers and controlled texture from fractal noise and turbulent displacement. A parametric scenery kit starts with building facades, lit windows, and foliage. Its textures have stable surface coordinates and seeds. `look.depth` blur, `look.pool` light, and `look.fade` haze supply depth cues; a separate depth/ordering contract controls parallax and occlusion.

Information stays vector and exact: captions, cards, lower thirds, tickers, map lines and labels, and the show's marks. It takes no posterize, displacement or paint texture. Caption looks keep their approvals ([ADR 0048](docs/decisions/0048-caption-looks-are-approved-and-measured.md)), and sizes on a map stay formulas on the engine's native map ([ADR 0057](docs/decisions/0057-map-kit.md)).

One shared lighting model and one finish owner bind the image. The light rig may contain key, fill, ambient, and rim lights, with common transforms, colors, intensities, and shadow settings; `plates.stage_lights()` already returns such a rig. A 2D adapter derives its local light direction and shade palette from that rig, including after a pose or camera change. A style with no modeled light, such as Ink or Cel, explicitly opts out of form lighting.

The style/show applies its world grade, bloom, and grain once after compositing the picture layers. Information is composited above that finish with its approved styling. An explicitly approved information treatment belongs to the information layer; a global texture or grade must not silently alter its measured colors or legibility.

## Shared space, camera, and contact

The proposed scene contract owns a single world unit and clock. Its canonical axes match [limbs.math3d](src/srstudio/limbs/math3d.py): x right, y down, z toward the reference viewer. Every asset declares its scale into those units and a local-to-world transform. Rig reference pixels, mesh units, and image pixels are never treated as interchangeable by inference.

`composition.plate_view` now supplies a [perspective registration bridge](docs/composition-preflight.md#register-a-plate-view): canonical units and handedness, complete parent transforms, shared world lights, and bounded overscan for an off-center principal point. Its image offset is already projected. A real-render landmark test checks this mapping. `prepare_plate` verifies static untextured geometry and prepares closed scene/resource bundles in a bounded worker; textured/animated and proxy adapters, plate/proxy emission, orthographic support and the full animated proof remain open.

One camera owns projection. A 2D point travels from local geometry through its world transform and view/projection, then through the inverse of its drawing parent's 2D transform. [limbs.projection.Camera](src/srstudio/limbs/projection.py) already implements that last contract. A plate adapter must derive the engine camera's handedness, field of view, principal point, and pixel scale from the same camera and pass landmark registration tests. The separate [plates.Camera](src/srstudio/plates.py) and [2D group camera moves](src/srstudio/camera.py) are existing mechanisms, not interchangeable camera objects. A composited plate and its attached marks must not receive the camera transform twice.

Depth ordering is explicit. Fixed, nonintersecting planes may use declared back-to-front order. A hand wrapping a mug, or a figure walking behind a car and then in front of it, requires depth/part masks or explicitly split passes sampled at the same time. Alpha alone cannot resolve internal occlusion. `srstudio.proxy` gets a part-id pass from the plates API by rendering flat emissive part colours, and `layers` cuts it into back, front and under plates so people draw between them. A depth or normal pass must still be proven available on the chosen backend.

A contact names the actor anchor, prop/surface anchor, their world transforms, and the time interval in which they agree. A shadow names both caster and receiver. A receiver must provide a plane/mesh proxy or an authored shadow mask bound to its pose; a flat RGBA plate supplies neither world normals nor a receiver by itself. Self-shadows use the same rule. Unknown receivers, intersecting layers without an occlusion strategy, and camera views outside a rig's envelope fail preflight before scene mutation or rendering. A deliberately flat style may declare shadows off; a requested unsupported shadow is never silently omitted.

## Style conversion and temporal continuity

The [effect shader](https://github.com/pedroanisio/scene-render/blob/af179e456d29f5bbc82c86187cccd620cf0e3124/crates/sr-gpu/src/effects.wgsl) posterizes encoded RGB channels, maps luminance through a gradient, and constructs outlines from alpha morphology. This can stylize a silhouette, but does not separate illumination from material color or find interior creases. A multicolored car must retain distinct paint, glass, tires, and markings under light changes.

The default is the material-aware ramp in `srstudio.proxy`: a light pass cut into tone bands per part, with interior ink where part families meet on the part-id pass. Palette, band thresholds, line width units (screen pixels or world units), color space, premultiplied alpha handling, and effect order are versioned style settings. A silhouette-only result is acceptable only for a style that explicitly wants it. No recipe is adopted solely because its XML validates.

Animation obeys these contracts:

- Paint and displacement are anchored to object/rig coordinates. Seeds derive from stable scene, asset, and channel identifiers, never evaluation order or wall-clock time. Intentional animated grain/noise has an explicit clock and rate. Rebuilding a frame, or sampling it out of order, gives the same result on the pinned renderer configuration.
- Shade anchors, rim regions, masks, and contact shadows follow the same pose sample as the drawing. Threshold crossings must not introduce unapproved band flicker. A held pose with held lights and camera keeps its surface texture and shade unchanged.
- Continuous pose segments preserve position and velocity at joins; cuts, replacement poses, and animation on twos declare their discontinuities. Texture phase, expression state, gaze targets, and contact constraints carry through continuous shot segments. A cut changes the camera without implicitly resetting actor state.
- Rigs retain their motion limits, limb constraints, lip sync, and expression vocabulary. A lighting layer cannot drive biomechanics or replace an emotional pose. New views and expression transitions need registered drawings or a validated deformation model; they cannot be extrapolated from one frontal drawing.

## Agent-facing composition contract

The table defines the complete target contract. [srstudio.composition](src/srstudio/composition.py) implements manifest records, declared relationship checks and verified vector emission; the [composition guide](docs/composition-preflight.md) distinguishes those supported features from pending adapters and runtime enforcement.

| Record | Required content | Refusal before any rendering |
|---|---|---|
| `ScenePlan` | Explicit style/part versions, output dimensions, rational fps, duration, seed, world unit, camera, lights, ordered layers, contacts, and budget | Unknown fields/references, non-finite values, invalid dimensions/time, unapproved versions |
| `CameraSpec` | View/projection, unit conversion, near plane, output mapping, supported view envelope | Near-plane crossings, singular parent transforms, inconsistent or double projection |
| `LightRig` | Typed key/fill/ambient/rim records and a declared flat/lighted style mode | Unsupported light kinds, invalid intensities/directions, missing shading adapter |
| `LayerSpec` | Drawing/mesh/plate reference, local transform, depth strategy, surface coordinates, caster/receiver bindings | Missing receiver or pass support, unsupported intersections, picture effects on protected information |
| `TemporalPolicy` | Scene-time mapping, continuous/held/cut intervals, deterministic noise channels and actor state | Undeclared discontinuities, invalid contacts or motion bounds, unsupported poses |
| `RenderBudget` | Finite limits for output frames/pixels, unique new plates, engine invocations, samples, bounces, memory, and per-invocation timeout | An unbounded or over-budget plan; retries also consume the invocation budget |

The proposed preflight parses strict typed input, checks the whole plan, resolves capabilities and asset versions, and returns an immutable validated plan plus a cost estimate. Emission consumes that plan. Errors carry a stable code, field path, offending value/reference, and a remedy, so an agent can repair its request. Failed validation leaves both the scene and render cache untouched. Runtime budget exhaustion cancels work with a typed error and never publishes a partial output. Existing typed failures such as `LimbError`, `HeadMotionError`, and `PlateError` remain the underlying causes.

### Runnable example with current APIs

This example demonstrates typed projection through a transformed drawing parent, an existing shade primitive, a reusable light rig, and protected information above a world finish. It does not render a 3D object, cast a contact shadow, or implement the proposed scene compiler. The `lighting` value is ready for an existing plate definition; it does not automatically light the 2D shade.

```python
from sr_core.scene import Scene
from srstudio import Canvas, brush, look, plates
from srstudio.limbs.math3d import Vec3
from srstudio.limbs.projection import Affine, Camera
from srstudio.toon import shape_d

scene = Scene(version="auto")
scene.add_project(width=1080, height=1920, fps="24", duration=1, seed=1030)
cv = Canvas(scene, font_asset=None)
world = cv.group(cv.comp, "world", x=40, y=60, scaleX=2, scaleY=2)
parent = Affine(a=2, d=2, e=40, f=60)
camera = Camera(
    projection="perspective", distance=10, focal=10, scale=100, origin=(540, 960)
)
contact = Vec3(1, 2, 0)
point = camera.project(contact, parent=parent)
cv.ellipse(world, point.xy[0] - 12, point.xy[1] - 12, 24, 24, "#d09060")
shade = brush.crescent(((0, 0), (24, 12), (0, 24)), 6, (-12, 12))
cv.path(world, shape_d(brush.outline(shade)), fill="#a06040")
lighting = plates.stage_lights(warm=True, rim=True)
look.grade(cv, world, "world-finish", {"vignette": {"amount": 0.1}})

information = cv.group(cv.comp, "information")
cv.rect(information, 80, 1700, 920, 120, "#ffffff")
assert scene.check() == []
```

The [document tests](tests/test_drawing_document.py) execute this example, check projection and layer placement, exercise typed camera failures, compare deterministic rebuilds, resolve local evidence links, and check that renderer source links pin a commit. Run `python -m unittest discover -s tests -p 'test_drawing_document.py' -v` from the repository with its Python dependencies installed. These checks establish API/structure correctness; visual acceptance belongs to the proof below.

## Video types

The table gives each type its default. Only the rigid-object layer is built, and each type's first use of a layer goes through the proof described below.

| Type | Draws today | Takes first | Keeps |
|---|---|---|---|
| Toon | Heavy ink on gradient and lit rooms | Every layer; it is the first user | Its rigs and caption pill |
| Cutout | Flat vector shapes, soft gradients, bold outlines | Rigid objects, reduced to flat shapes | Its flat rooms |
| Collage | Paper cut-outs with hand-cut edges on painted sets | Environments; rigid objects reduced to paper | Its paper people and shadows |
| Gloss | Vinyl dolls with shaded form in a pastel plaza | Rigid objects, environments | Its inner-shadow form |
| Saga | Navy ink and gold rim light on deep space | Rigid objects, form shading | Its grade and rim light |
| Stick | Stick figures traced at 12 fps on painted, flat-shaded sets | Rigid objects, environments | Its figures |
| Soft | Round white blobs on a flat warm stage | Rigid objects, only when a prop must turn | Its figures and flat stage |
| Ink | One ink and one grey on white paper | Rigid objects, as line alone | No shading, no colour bands |
| Cel | Traced, filled drawings under a measured camera | None; it is traced from its source | All of it |
| Mind | Toon faces on its own stage, with cards | Environments | Toon's rigs and its cards |
| News | A plum set with monitors, anchors on rigs | Rigid objects, environments | Its graphics, as information |
| Host | Rafa, modeled, on path-traced plates | Already on rigid objects and plates | All of it |
| Maps | The engine's native map, with cards | None; it is information | All of it |

## Rules

- **New videos only.** Published reels are frozen ([ADR 0040](docs/decisions/0040-frozen-releases-at-an-accepted-drawing.md)). The method is where new work starts, not a switch on existing builders, so a published reel or an approved part changes nothing. A rebuild with unchanged inputs and the pinned toolchain keeps its approved scene and specimen fingerprints. No accepted style or asset is silently upgraded.
- **Proof for each look.** A type takes a layer for the first time through a rendered, animated clip that the operator approves, and a changed drawing is a new part version ([ADR 0047](docs/decisions/0047-character-versions.md)). Style recipe, srstudio and sr-core revisions, schema, renderer build, quality settings, and approval evidence are recorded together.
- **Same gates.** Every render passes the engine's `--strict` encode, and every first delivery passes the frame gates and the full-size review ([ADR 0073](docs/decisions/0073-frame-gates-and-standing-review.md)). That ADR is still proposed and was written for Okayville batches, and `publish_pilots.py` does not run the frame gates, so this rule extends them to every video type. Existing caption/map geometry and approved colors remain intact.
- **Cache per render input.** Plates are cached under `generated/` with renderer-owned identities ([ADR 0095](docs/decisions/0095-rendered-artifact-cache-identity.md)). The implementation namespaces artifacts by renderer binary hash and includes compiled quality settings, print scenes and actual font bytes in their keys. The stable drawing digest remains separate. Changed poses, camera, lights, materials, maps, or recipe invalidate the relevant outputs. An unchanged rebuild renders zero new plates, while still reading identity inputs. Neither camera motion nor path tracing is described as free.

## Proof and acceptance gates

The first full proof is a short Toon clip containing a multicolored car turning under a moving camera, a rigged hand holding a prop, a figure crossing behind/in front of the car, a textured background, and protected information. It includes a held pose, a continuous pose/expression transition, a cut, changed key/fill/rim lighting, and a warm-cache rebuild. Test frontal, three-quarter, and profile views only for assets that explicitly support them; an unsupported view must demonstrate the refusal path.

The thresholds below are acceptance targets, not reported measurements, except where ADR 0091 records one. That proof records its results and any approved style-specific replacement thresholds.

| Gate | Required evidence |
|---|---|
| Registration and contact | Corresponding 2D/3D landmarks and held contact anchors differ by at most 1 output pixel at 1080×1920 over the declared camera envelope; test transformed parents and near-plane rejection |
| Occlusion and shadows | Expected front/back masks agree away from a 1-pixel antialias boundary; no missing/doubled shadows; receiver and contact anchors remain within the same 1-pixel tolerance |
| Palette and edges | Interior cel-band pixels match an approved palette entry within 2 levels per 8-bit RGB channel before the final grade; interior edges and screen/world line-width behavior are explicitly approved |
| Temporal stability | With pose/camera/light/noise time held, repeated world frames match byte-for-byte on the pinned configuration; out-of-order evaluation matches sequential evaluation. No unapproved texture swimming, edge popping, or band flicker in the animated clip |
| Continuity | Continuous joins differ by at most 1 output pixel in position and 1 pixel/frame in one-sided velocity; held/replacement/cut events are tagged and reviewed separately; gaze, expression, and contacts persist across continuous segments |
| Information | Its geometry, styling, and isolated pixels match the existing approved layer; the composited output passes caption contrast and safe-area gates |
| Compatibility | Existing scene/specimen fingerprints and frozen-release checks pass with the feature disabled; enabled variants receive new style/part versions |
| Cost and determinism | Record hardware, engine, srstudio and sr-core hashes, frame count, unique plates, cold/warm render work, peak memory, and quality settings. Work stays within the declared budget, unchanged rebuilds invoke no plate renders, and changed render inputs invalidate their cache entries |
| Failure behavior | Invalid views, missing passes/receivers, conflicting transforms, unknown fields, and excessive budgets produce typed actionable errors before scene/cache mutation |

If a recipe fails, it stays unavailable for that style, and the style keeps drawing as it does today. A schema-valid or visually promising still cannot satisfy the animated gates.

## Alternatives and trade-offs

- **All 2D:** preserves direct artistic control and remains appropriate for fixed views and intentionally flat styles. It requires authored views or deformation rules when unseen surfaces become visible.
- **All 3D:** provides shared geometry and lighting, but does not by itself preserve approved linework, expressive rigs, typography, or render cost. It is not a requirement for every video type.
- **RGB postprocessing alone:** is inexpensive to compose, but lacks material/light separation and interior geometric edges. It is available only where those limitations meet the style contract.
- **Direct rendering of every frame versus cached plates:** direct rendering supports continuously changing inputs; plates reuse genuinely repeated inputs. The first full proof chooses using measured work and continuity, with the same bounded budget for either path.
