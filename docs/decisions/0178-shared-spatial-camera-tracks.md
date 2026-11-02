---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0178: Share scene cameras with spatial interaction baking

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

Spatial hands and props must use the same camera and resolved parent pose as
their surrounding composition. `composition.spatial_camera` derives a spatial
camera from a revalidated scene plan, folding the selected world layer's parent
transform into the camera once. Geometry remains in its original source units.
An independent camera configuration was rejected because it permits registration
drift; transforming geometry as well would apply the parent twice.

`scene_motion.spatial_cameras` converts a revalidated timeline into immutable,
bounded held camera samples. Interaction baking merges these scene-clock cuts
with its frame grid, retaining exact authored times for camera selection while
sampling geometry on its local performance clock. Subtracting and re-adding an
offset was rejected because floating-point rounding can select the preceding
camera at an authored cut. During inferred released-prop holds, geometry freezes
at the source endpoint while the scene camera continues.

All projections and timing intervals are validated before scene mutation. Camera
cuts count toward existing frame and node budgets, and intervals must remain
distinct at the scene format's six-decimal time precision. Single-limb compilers
retain their static-camera contract. The bridge does not extend plate projection
capabilities, supply shared shading, or replace the animated DRAWING proof.

The [spatial registration guide](../composition-preflight.md#register-a-spatial-camera),
[registration tests](../../tests/test_composition_spatial_camera.py), and
[camera-track tests](../../tests/test_spatial_camera_tracks.py) cover the contracts.
