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

The default source sampling is 12 fps, held on a 24 fps output: animation on
twos. The character remains a frontal billboard. Its expression replacement at
3.2 seconds and depth-pass replacement at three seconds are explicit cuts.
These are not evidence of continuous expression blending or whole-body walking.
The ground shadow is an authored planar mask, not a simulated receiver shadow.

## Build and measure

Run from the repository root in an environment with srstudio and its test
dependencies installed. DejaVu Sans Bold and the pinned renderer must be
available. Each output directory must be new; the shared cache may already exist.

```sh
python -m examples.drawing_proof ../generated/drawing-hybrid-candidate/v1/cold \
  --engine ../generated/bin/scene-render \
  --cache ../generated/drawing-hybrid-candidate/v1/cache

python -m examples.drawing_proof ../generated/drawing-hybrid-candidate/v1/warm \
  --engine ../generated/bin/scene-render \
  --cache ../generated/drawing-hybrid-candidate/v1/cache --warm-only

python -m examples.drawing_proof_review \
  ../generated/drawing-hybrid-candidate/v1/warm/scene.xml \
  ../generated/drawing-hybrid-candidate/v1/review \
  --engine ../generated/bin/scene-render
```

`--warm-only` sets the renderer invocation allowance to zero. A missing cache
entry fails instead of silently rendering. The default cold allowance is 28
invocations for 14 views, at 48 samples, four bounces, and one-times oversampling.
Each renderer gets a 120-second execution deadline and an 8 GiB address-space
limit. The shared GPU lock serializes engine work. Waiting for that lock is
separate from renderer execution time.

The build report records actual work, input hashes, the installed schema hash,
font bytes, the pinned Bento part, quality settings, and Linux process memory
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

The production composition compiler requires approved part versions. This car
is new candidate geometry, so the fixture uses the existing `proxy.layers`
proof path and an explicit centered-camera adapter for the hand. It does not
reuse an unrelated approved part name to pass preflight. The adapter's tests
compare against `proxy.View.project` and exercise near-plane refusal.

The following acceptance work remains: measured raster landmark/contact and
occlusion masks across the complete clip; palette and line-width approval;
continuous pose/expression and whole-body support; shared drawn shading and
caster/receiver contracts; equivalence to the approved information layer;
compatibility fingerprints; and complete temporal visual review. The JSON
reports distinguish measured facts from those remaining requirements. Operator
approval belongs after the completed proof, as required by DRAWING.md.

Run the fixture and measurement tests with:

```sh
pytest tests/test_drawing_proof_example.py tests/test_drawing_proof_review.py
```

## Recorded candidate

The [retained review](../../generated/drawing-hybrid-candidate/v1/index.html)
contains the six-second, 144-frame strict encode and sampled full-size PNGs.
Its [verification record](../../generated/drawing-hybrid-candidate/v1/verification.json)
records 28 cold raw-car invocations, 14 views, zero-invocation warm builds,
identical rebuilt scene/image bytes, and passing repeated-frame and information
pixel checks. Rendering used engine 0.8.0 on llvmpipe's software Vulkan adapter.
The source and artifact hashes distinguish the final candidate from earlier
failed and superseded iterations retained alongside it.

The targeted validation passed 63 tests and 32 subtests, with 93.06% branch
coverage across the two new example modules. Full-size frame inspection caught
and corrected hand/face overlap and a foreground figure clipped at the left
edge. These observations do not certify the remaining acceptance gates or a
complete temporal visual review. The hand remains an isolated spatial study,
and the cup's support outside its attached interval is not modeled.
