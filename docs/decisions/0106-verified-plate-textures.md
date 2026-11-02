---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0106: Preserve authored textures in bounded plate preparation

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

Composition preparation owns immutable snapshots of UV coordinates and RGBA8
pixels. A host can snapshot existing clay meshes and plate materials with
`plate_source`, or construct the same closed records explicitly. Color maps,
normal maps, their strength, sheen and subsurface settings survive the adapter.
[Printed-label support](0144-bounded-composition-prints.md) adds a separate bounded
adapter for rendering work and font inputs; dropping a label would change the drawing.

Every texture is named by an ID that a material references. Source validation
bounds counts, dimensions, raw bytes and scalar ranges. The worker verifies
reference completeness and finite per-vertex UVs, then generates PNG and OBJ
resources. Texture coordinates stay attached to source vertices through geometry
transforms; generating or clamping a UV map would alter an authored surface.
The same PNG encoder serves ordinary plate files and composition resources.

Resource names bind the exact encoded file. PNG headers include dimensions, so
reshaping otherwise identical raw pixel bytes cannot reuse another image's path.
The source identity also binds dimensions, pixels, UVs and all material fields.
Existing untextured defaults retain their version-1.0.0 identity; extended inputs
use version 1.1.0. The parent checks content-addressed paths and the combined
resource limit, and bundle compilation reverifies source evidence before cache
mutation. Renderer cache keys already include the compiled XML and resources.

External image paths, implicit float-to-byte conversion, callbacks, and host-side
PNG compression were rejected because they respectively add mutable dependencies,
change pixels silently, introduce executable inputs, and escape the worker budget.
Copying bounded arrays remains a host operation. Encoding, geometric verification
and document validation run under the plan's process limits.

The [tests](../../tests/test_composition_textures.py) verify snapshots, legacy
identity parity, an authored Rafa knit material, UV basis parity, repeated UVs,
shape-sensitive resources, cache invalidation, refusal paths and real-render
orientation with warm-cache reuse. This is evidence for material transport,
not approval of a new drawing or an animated texture policy.
