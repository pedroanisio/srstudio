---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0087: Normalize character clips through a container clock

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

The opt-in `character_clips` boundary accepts typed Actor, split-head Toon, Gloss and prepared plate performances.
An explicit start/end interval belongs to the parent timeline. All performance tracks use seconds from the clip
start. A timed group with `timeOffset=start` maps that local clock exactly once, including native limb tracks and
procedural idle. Builders emit on the inherited clock; the adapter then expresses composition keys relative to
their owning node's source start. This preserves their phase when sequence placement shifts node lifetimes
without shifting composition keys. Existing local/normalized keys retain their semantics. The caller's canvas
setting is restored afterward. Placement maps a declared source anchor to parent coordinates without guessing anatomical
correspondence between styles.

Adapters validate supported controls, vocabularies, references, time ranges and work bounds before emission.
Scene/canvas transactions restore failed drawing mutations. Plate assets are prepared and registered separately;
the boundary performs no implicit rendering, asset copying or filesystem rollback. Rafa sheet conversion binds
full-body and patch assets, preserves their pixel positions and source duration, and coalesces identical frames.

Actor gains an optional canvas-clock `end` for limb lifetime. Without it, project-duration behavior remains.
This prevents a short character clip from baking a longer root track through the entire project. Rosa's stitch
validation moves into the existing performance-validation hook, preserving validation and drawing while sharing
the base lifecycle. Unknown overridden Actor lifecycles are refused by the clip adapter.

## Verification

Engine evaluations compare zero-offset and nonzero-offset performances for all four adapters, both canvas clock
settings, procedural movement, layered plates and limb tracks with their own local offsets. Nested sequence shots
verify keyed state and animation phase as well as parent-clock composition and source-anchor placement.
Tests also cover unsupported controls before
geometry, malformed inputs, rollback of failed drawings, explicit root-bake lifetime, legacy behavior and an
executable two-family documentation recipe.

## Alternatives and limits

Shifting only authored keys misses procedural idle and native animation. Editing every emitted timestamp risks
double offsets and corrupting local clocks. Cloning a canvas would duplicate ID counters and asset caches.
Inferring adapters from parameter names would misread Toon exit times and confuse model builders with drawing
functions. An explicit typed union and an engine container clock avoid these failure modes.

This boundary does not implement shared acting intent, carry state between separate clips, normalize anatomy,
or certify emotional/biomechanical quality. Specialized builders remain available. The current Toon adapter
supports the shared pose vocabulary and Bento's extensions; custom drawing-specific vocabularies remain with
their explicit builders. The API is Python authoring, not a decoder for model-generated JSON.
