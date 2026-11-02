---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0196: Authored surface fields connect vectors to shared scene lights

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

The hybrid compiler needs drawn surfaces to respond to the same world light rig
as rigid objects while preserving their authored palette and ink. An arbitrary
2D outline does not determine a 3D normal. Inferring geometry or relighting the
final RGB image would invent hidden form or mix material color with illumination.

The host therefore supplies immutable surface points, unit normals and palettes
per source shape. Explicit ink fields retain authored fills and strokes. Fields
may have bounded source-clock pose keys; the host owns their alignment with the
drawing. Complete layer parent transforms move points and normals into world
space once. Shared ambient, directional and sphere-area lights produce linear
RGB energy, mapped to the nearest authored palette color. Sphere-area evaluation
uses an explicit center-direction approximation and requires later calibration
against plate rendering; it does not claim path-tracing equivalence or occlusion.

Fields are part of source identity and resource bounds. Preparation verifies
shape references, and workers repeat semantic checks. Static compilation refuses
keyed fields. Timeline planning adds mapped source keys and bounded frame samples,
and includes selected colors when deciding whether adjacent spans can merge.
This prevents a source-pose change disappearing when the scene camera/light plan
is otherwise unchanged. Evaluation is random-access and does not retain state.

Automatic normals, implicit shape selection, unbounded frame expansion, and
silently shading only some shapes were rejected. Every shape declares its role;
native information stays in separate screen layers. Existing vector camera
envelopes remain enforced. Receiver shadows, world finish, full hybrid migration
and adoption evidence remain separate unfinished requirements.

The [guide](../composition-preflight.md#author-vector-form-lighting) contains an
executable example. [Contract tests](../../tests/test_composition_forms.py) cover
input failures, source hashes, transformed fields, palette selection, worker
revalidation, source-clock cuts and strict rendered pixels.
