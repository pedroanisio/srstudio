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
`drawing_proof` still builds its retained candidate through the legacy path;
the spatial hand, protected information and complete acceptance matrix
have not yet moved into this world timeline. The combined candidate below adds
the native figure. No existing drawing or approval
changes. Run `pytest tests/test_drawing_world.py` with `SRSTUDIO_ENGINE` set to
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
the rig retains its authored ink colors. Hand, protected information, body
support, rig form lighting and the complete animated acceptance measurements
remain open. The retained legacy `drawing_proof` and the 30-second showcase are
unchanged.

The [combined-component verification](../../generated/sdk-world-figure/v2/verification.json)
records six exact 1080×1920 pixel comparisons with the unchanged native figure,
including both sides of the camera cut. A separate 216×384 mixed build reuses
eight verified cached car renders with zero new engine invocations; its opening
pixels at 0 and 0.25 seconds match exactly. These checks establish native drawing
and clock preservation, not complete body support or raster-contact acceptance.

The production composition compiler requires approved part versions. An explicit
[candidate-review workflow](composition-preflight.md#review-a-new-candidate-drawing)
now accepts independently named, content-pinned new geometry through the shared
compiler. This fixture still uses the existing `proxy.layers` proof path and an
explicit centered-camera adapter for the hand; migration to that shared workflow
remains part of the combined proof. It does not reuse an unrelated approved part
name to pass preflight. The adapter's tests
compare against `proxy.View.project` and exercise near-plane refusal.

The following acceptance work remains: measured raster landmark/contact and
occlusion masks across the complete clip; palette and line-width approval;
rendered pose/expression continuity and whole-body support; shared drawn shading
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
