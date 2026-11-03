---
generated-by: OpenAI Codex (GPT-6)
---

# Hybrid drawing candidate

[drawing_proof.py](../examples/drawing_proof.py) builds a six-second, 1080×1920
candidate for the [DRAWING acceptance matrix](../DRAWING.md#proof-and-acceptance-gates).
It is an executable review fixture, not an adopted style or a completed proof.

The original car has separate paint, glass, tire, lamp, and trim materials. It
turns while the camera moves between 0.5 and 1.5 seconds. At four seconds the
camera cuts and key/fill/rim powers change. A spatial hand carries a cup on the
same performance clock through that cut. Bento appears behind the car, passes
its left end, and appears in front. Ground texture stays in authored world
coordinates; information stays in screen coordinates above the picture.

World and hand samples default to 12 fps, held on a 24 fps output. The opt-in
Bento face deforms at 24 fps: neutral becomes concerned over 2–2.7 seconds,
then concerned becomes deadpan over 3.6–4.6 seconds. The second transition
continues through the camera cut on its original clock. Head pose changes share
those intervals; no opacity crossfade substitutes for authored face geometry.

The character remains a frontal billboard. Its depth-pass replacement at three
seconds is still an explicit cut, not whole-body walking. Intermediate faces
carry their candidate rig identity and no drawing approval. The ground shadow
remains an unbound authored mark; adopting the new receiver-mask contract is
part of the migration to the shared compiler.

## Build and measure

Run from the repository root in an environment with srstudio and its test
dependencies installed. DejaVu Sans Bold and the pinned renderer must be
available. Each output directory must be new; the shared cache may already exist.

```sh
python -m examples.drawing_proof ../generated/drawing-hybrid-candidate/v2/cold \
  --engine ../generated/bin/scene-render \
  --cache ../generated/drawing-hybrid-candidate/v2/cache

python -m examples.drawing_proof ../generated/drawing-hybrid-candidate/v2/warm \
  --engine ../generated/bin/scene-render \
  --cache ../generated/drawing-hybrid-candidate/v2/cache --warm-only

python -m examples.drawing_proof_review \
  ../generated/drawing-hybrid-candidate/v2/warm/scene.xml \
  ../generated/drawing-hybrid-candidate/v2/review \
  --engine ../generated/bin/scene-render
```

`--warm-only` sets the renderer invocation allowance to zero. A missing cache
entry fails instead of silently rendering. The default cold allowance is 28
invocations for 14 views, at 48 samples, four bounces, and one-times oversampling.
Each renderer gets a 120-second execution deadline and an 8 GiB address-space
limit. The shared GPU lock serializes engine work. Waiting for that lock is
separate from renderer execution time.

The build report records actual work, input hashes, the installed schema hash,
font bytes, the candidate figure rig, quality settings, and Linux process memory
high-water marks. These memory measurements do not include GPU memory and do not
measure simultaneous aggregate RSS. Candidate car/recipe identities carry no
approval. No part table or approved drawing is changed.

The review command validates the scene, runs a strict full-quality encode,
renders full-size frames including repeated out-of-order requests, and checks
decoded RGBA equality. It requires an initial held frame, visible world changes,
and unchanged pixels in the information rectangles. It preserves engine logs,
the video, PNGs, and a scoped JSON report. A failed command or pixel check does
not produce a passing review report. View the retained frames at full size and
watch the entire video separately.

## Contract boundaries

### Shared world inputs

[`drawing_world.world_scene`](../examples/drawing_world.py) provides the car,
textured floor and receiver mask as a candidate-review timeline for the shared
compiler. It retains one immutable car mesh and moves it with world transforms;
the floor's 67 polygons carry actual spatial vertices. The shared camera owns
their projection. The authored shadow ellipse names its caster, receiver,
surface, anchors and directional key, and turns with the car. All four tire
bottoms sit on the floor, correcting a 3 cm penetration in this new candidate.
The ellipse is an authored mask, not a traced silhouette shadow.

The plan retains the original fourteen held world views, camera cut and light
changes. Its declared sample allowance accounts for the full 28 raw render jobs
at 48 samples per pixel. Native source, XML and worker limits remain enforced.
Planning performs no rendering or file writes. For example:

```python
from pathlib import Path
from examples.drawing_world import world_scene
from srstudio import scene_motion

study = world_scene()
result = scene_motion.emit_timeline(
    study.timeline, study.vectors,
    Path("../generated/drawing-world/cold"),
    engine=Path("../generated/bin/scene-render"),
    cache=Path("../generated/drawing-world/cache"),
)
print(result.work)
```

This world input is a component of the combined-proof migration. The original
`drawing_proof` still builds its retained candidate through the legacy path.
The combined components below add the native figure, spatial hand/cup and
protected information to this shared world. The complete acceptance matrix
remains open. No existing drawing or approval changes.
Run `pytest tests/test_drawing_world.py` with `SRSTUDIO_ENGINE` set to
exercise numeric registration, transformed parents, tire contact, receiver
failures and real-render cold/warm equivalence.

The [world-component verification](../../generated/sdk-world-composition/v1/verification.json)
records 2,828 projected landmarks across the fourteen full-size views, with a
maximum coordinate residual below `1e-12` pixel. Its separate 216×384 render
test uses four views: eight cold raw renders, zero warm invocations, identical
compiled bundles, identical held/repeated pixels, and changed motion/cut pixels.
These are component measurements, not full-size raster registration or approval
of the complete animated proof.

### Combined candidate

[`drawing_figure.figure_scene`](../examples/drawing_figure.py) extends the shared
world inputs with the actual 977-shape native figure. One explicit ink group
preserves its drawing, gradients, opacity and animation. Two painter windows
retain the same performance clock across the declared depth cut at three
seconds; the camera cut at four seconds also keeps that clock. World placement
uses the shared perspective camera and an authored centimeter scale. The figure
remains frontal, and requesting an unsupported profile is refused.

The default plan samples the world at 12 fps on a 24 fps output; repeated values
in the held opening merge into 66 intervals. The car still
requires only 28 raw jobs for its fourteen distinct views. Unchanged floor
intervals coalesce after native geometry reuse, keeping the complete vector
output within the existing eight-MiB cap. Use `figure_scene()` in the build
snippet above to compile these combined picture layers.

This candidate declares a ground-level root; it does not yet constrain each
sole with the body solver. The three-second depth change remains a cut, and
the rig retains its authored ink colors. The following components add the hand,
supported body and information. Rig form lighting and the complete animated
acceptance measurements remain open. The retained legacy `drawing_proof` and
the 30-second showcase are unchanged.

The [combined-component verification](../../generated/sdk-world-figure/v2/verification.json)
records six exact 1080×1920 pixel comparisons with the unchanged native figure,
including both sides of the camera cut. A separate 216×384 mixed build reuses
eight verified cached car renders with zero new engine invocations; its opening
pixels at 0 and 0.25 seconds match exactly. These checks establish native drawing
and clock preservation, not complete body support or raster-contact acceptance.

The [sole-anchor regression](../../generated/sdk-world-figure/v3/verification.json)
corrects a drawing/reference-space mix-up: Bento's authored sole coordinate
must pass through his reference mapping before conversion to native pixels.
The previous root used native y=1479.53 instead of 1806.81. All 17 figure tests,
including six full-size native pixel comparisons, pass with the corrected
placement. This fixes the static anchor in `figure_scene`; the supported-body
component below adds animated per-foot constraints.

### Shared hand and cup

[`drawing_hand.hand_scene`](../examples/drawing_hand.py) adds a scene-lit hand and
cup sequence to the combined picture. This is newly authored candidate geometry:
tapered tubes follow every arm and digit joint, a closed palm prism uses the
rig's palm corners and thickness, and the cup follows the existing attachment
track through the camera cut and release. Four explicit palettes retain sleeve,
skin, cup and coffee material identities. The existing native Toon hand adapter
and legacy proof remain unchanged for comparison.

All meshes declare centimeter scale and clay handedness. The compiler owns
their shared camera, lights and depth testing, including finger/cup occlusion.
The opening holds the 0.5-second pose; later snapshots use original motion time.
At the default 12 fps, the combined picture has 66 intervals and declares 160
actual raw render jobs: 28 for the car and 132 for hand geometry/view pairs.
An unchanged rebuild reuses verified renders. This work is explicitly included
in the candidate budget; no core limit is raised.

The [hand-world measurements](../../generated/sdk-world-hand/v1/measurements.json)
check 7,062 projected landmarks over all 66 full-size intervals, including cup
vertices and the actual arm/digit joints. The maximum coordinate residual is
below `1e-12` pixel. The conservative full plan declares 439,378 nodes and
6,075,706,784 bytes of working storage, within the existing 500,000-node and
8-GiB limits. These are numeric registration and planned-cost measurements;
they do not measure rendered skin contact or observed peak memory.

The retained 216×384, 2-fps-world render test completes 30 cold raw jobs and
rebuilds with zero warm invocations. Bundle bytes and source identities match;
held and out-of-order repeated frames are pixel-identical. Visual inspection
shows the hand/cup as an isolated study above the car, not an arm attached to
the native figure. These component checks do not establish whole-body integration.

Use `hand_scene()` in the build snippet above to include this drawing. Its new
volumes and palette still require the complete animated acceptance review and
operator approval. This stage does not establish collision-free skin surfaces,
the full-size contact/occlusion thresholds, character body support, character
form lighting or approved information-layer equivalence.

### Shoulder-attached candidate

[`drawing_attached.attached_scene`](../examples/drawing_attached.py) supplies
the attached arm used by the supported-body candidate below. It keeps the
native face and head clock, declares the candidate's right arm as externally owned, and omits that
native arm before drawing. The spatial sleeve follows Bento's actual shoulder,
including native breath and lean. Its rigid placement preserves arm and digit
dimensions. The cup follows the same placement while attached and holds its
world pose before contact and after release.

The 1.2-second contact onset lies between regular samples. It now joins the
shared world schedule, so the camera, car, figure placement and hand geometry
all use that exact event. Adding only a hand snapshot and figure key was
insufficient: it turned the frontal figure toward an unsampled camera pose.
Event input is bounded and validated before planning.

The default plan has 67 intervals and 164 raw jobs. Each hand source snapshot
declares storage for both prepared passes; actual preparation of every snapshot
passes at both 2 and 12 fps. The timeline estimator distinguishes transient
raster preparation nodes from emitted image references when the original
estimate exceeds the node cap. The 500,000-node and 8-GiB caps remain unchanged.

The [native-engine registration report](../../generated/sdk-attached-hand/v4/registration/verification.json)
compares the projected native shoulder with the spatial sleeve in all 67
intervals at 1080×1920. Its maximum axis residual is below 0.0032 pixel.
This measures geometry registration, not raster contact masks. That component
still uses sliding feet; the supported-body replacement below adds sole
constraints and steps. Its cup's world hold after release does not model
physical support; the supported candidate adds fixed rests. Candidate geometry and palette still require
the complete acceptance review.

The [attached preview](../../generated/sdk-attached-hand/v4/index.html) uses
216×384 output and a 2-fps world cadence. Its event-aware build completes four
new raw renders and reuses 30 previously verified cache entries; the next build
uses zero renderer invocations and produces identical bundle bytes. Eight
strict final-quality frames include contact onset, the camera cut, release and
an out-of-order repeat. Opening/repeated pixels, the opaque background and
protected information regions match exactly. This is an incremental reduced
preview, not a fresh full-size cold run or complete acceptance.

### Supported body candidate

[`drawing_body.body_scene`](../examples/drawing_body.py) replaces the sliding
whole-figure placement in `complete_scene()`. Bento shifts over a stance foot,
lifts and places the other foot, transfers weight, and brings the trailing foot
along. His measured drawing proportions define a separate body profile; the
default human sole width remains 0.12 m. The solver preserves bone lengths and
checks its explicit static mass proxy. This is not a dynamics certificate.

The native upper body retains the face, breath and head clocks. Its pelvis
center follows the solved root, and the spatial sleeve follows the resulting
shoulder. Authored trouser contours deform through the hip, knee and ankle;
each foot is one rigid drawing placed at its world sole. Contour reduction
stays within 0.05 drawing units of the traced source polyline. It does not
replace that polyline with a generic foot or alter the approved native rig.

Liftoff, landing, weight-shift and hand-contact events join the shared sampling
clock. Both painter windows use the original six-second path clock, avoiding
rounding differences between locally offset path keys and global foot keys.
The three-second depth replacement remains an explicit cut. At the default
12-fps world cadence, the complete plan has 80 intervals and 196 raw render
jobs, with 178,661 planned nodes and 6,825,052,696 bytes of working storage.
These are planned costs, not observed peak memory or a completed cold render.

The native trunk faces each camera, so it turns at the four-second camera cut.
Nothing stays attached to that shoulder across the cut
([ADR 0215](decisions/0215-frontal-shoulder-camera-cuts.md)). The candidate
retimes the shared grip path to release the cup at 3.6 seconds, in its
pickup pose, and `check_cuts` refuses any carry held across a declared cut.
With the shared timing, the held cup moved 64 cm in world space at the cut.
Each rigid paw drawing takes its solved sole's yaw, so the toes follow the
solver's forward axis in every shot. A tilted sole raises an error.

`tests/test_drawing_body_support.py` exercises support, planted sole positions,
bone lengths, native pelvis registration, source preparation and full-size
component rendering. The component render isolates the upper body, legs, feet
and floor; the spatial arm, car and information belong to the combined render.
The [full-size body component](../../generated/sdk-bento-body/v4/index.html)
retains eight strict final-quality frames, including both steps, the held
opening and an out-of-order repeat. Its 5,775,010-byte XML stays below the
unchanged cap, and held/repeated RGBA pixels match exactly. This is component
evidence; the isolated render deliberately omits the spatial right arm.
At the 12 planted-sole observations in these frames, the last covered pixel
center in the projected anchor column is within 0.835 pixel vertically of that
anchor. The report records the local floor/interior checks and edge threshold;
this sampled measurement does not establish every frame's contact mask.

In `body_scene`, the cup stands on a fixed rest in each painter window. This is
Codex's `drawing_cup_support`: the rest's top is the cup's actual base at
pickup (1.2 seconds) or at the early release (3.6 seconds), and its foot is on
the floor. Both rests stay fixed in world space through the four-second camera cut.
A bounded rigid shoulder swing keeps the carried cup from entering a rest; bone
lengths and the finger/cup registration are unchanged. The rests add one
declared palette, which adds 132,700,744 bytes to the planned working storage.
`tests/test_drawing_supported_cup.py` covers contact, the floor, world fixity
and that palette. Shared rig form lighting and the full animated acceptance
matrix remain open.

### Native information in the combined scene

[`drawing_information.complete_scene`](../examples/drawing_information.py)
composes the picture layers with the original candidate's title, subtitle and
caption pill. Text keeps its native layout, explicit clipping, font bytes and
license. The screen information layer has no world parent or form-light fields
and remains above every picture layer.

The scene's native `background="#efe8df"` restores the original clear color
without inserting an extra picture layer. This retains the original text-edge
compositing path and adds no raw render jobs. At the default cadence, the
complete layer plan includes the supported candidate's 196 raw jobs and the existing
node, memory and output limits.

Use `complete_scene()` in the build snippet to include the background and
information. This reproduces the existing candidate layout; that layout itself
has no drawing approval. Equivalence to an approved information layer and the
complete rendered acceptance matrix remain required before adoption.

The full-size information test compares native and compiled 1080×1920 RGBA
pixels before and after the camera cut, with exact equality. The separate
[combined preview](../../generated/sdk-world-information/v4/complete-preview.json)
predates the supported-body integration and reuses 30 cached raw renders at
216×384 and a 2-fps world cadence. Its held and
repeated frames, opaque background, and title/caption regions pass exact pixel
checks. It is a reduced preview, not the default 12-fps full-size acceptance proof.

The production composition compiler requires approved part versions. An explicit
[candidate-review workflow](composition-preflight.md#review-a-new-candidate-drawing)
now accepts independently named, content-pinned new geometry through the shared
compiler. The retained legacy `drawing_proof` fixture uses the `proxy.layers`
path and an explicit centered-camera adapter for the hand; the new
`complete_scene` uses the shared compiler for every layer. Neither fixture
reuses an unrelated approved part name to pass preflight. The legacy adapter's tests
compare against `proxy.View.project` and exercise near-plane refusal.

The following acceptance work remains: measured raster landmark/contact and
occlusion masks across the complete clip; palette and line-width approval;
rendered pose/expression continuity and complete body-contact masks; shared drawn shading
and adoption of the caster/receiver contract; equivalence to the approved information layer;
compatibility fingerprints; and complete temporal visual review. The JSON
reports distinguish measured facts from those remaining requirements. Operator
approval belongs after the completed proof, as required by DRAWING.md.

Run the fixture and measurement tests with:

```sh
pytest tests/test_drawing_proof_example.py tests/test_drawing_proof_review.py
```

## Recorded continuous-face candidate

The [version 2 review](../../generated/drawing-hybrid-candidate/v2/index.html)
contains the current strict 1080×1920 encode: 144 frames at 24 fps over six seconds.
Its [verification](../../generated/drawing-hybrid-candidate/v2/verification.json)
records the nine sampled renders, exact repeated-frame and protected-information
comparisons, 23 example/review tests, and the separately passed real-engine
face cut-versus-uncut regression. Coverage of the two example modules is 61 of
72 branches (84.72%). The build reused the existing 14 car views with zero
renderer invocations; this is not a new cold-render benchmark. The full drawing
acceptance matrix remains open.

## Recorded first candidate

The [retained review](../../generated/drawing-hybrid-candidate/v1/index.html)
contains the six-second, 144-frame strict encode and sampled full-size PNGs.
Its [verification record](../../generated/drawing-hybrid-candidate/v1/verification.json)
records 28 cold raw-car invocations, 14 views, zero-invocation warm builds,
identical rebuilt scene/image bytes, and passing repeated-frame and information
pixel checks. Rendering used engine 0.8.0 on llvmpipe's software Vulkan adapter.
The source and artifact hashes distinguish the final candidate from earlier
failed and superseded iterations retained alongside it. That retained version
still contains the earlier expression replacement; it is not evidence for the
current continuous-face candidate.

The targeted validation passed 63 tests and 32 subtests, with 93.06% branch
coverage across the two new example modules. Full-size frame inspection caught
and corrected hand/face overlap and a foreground figure clipped at the left
edge. These observations do not certify the remaining acceptance gates or a
complete temporal visual review. The hand remains an isolated spatial study,
and the cup's support outside its attached interval is not modeled.
