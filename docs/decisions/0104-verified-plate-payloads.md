---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0104: Verify actual plate geometry before rendering

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

Manifest declarations alone cannot establish actual mesh bounds or render work.
`prepare_plate` verifies immutable snapshots of triangle meshes and typed material
records in the existing bounded worker. A closed binary-buffer representation
avoids pickle, callable builders and arbitrary resource paths. Bounds, normals,
indices and materials are checked before converting geometry to the shared plate
view. Host-side snapshotting only copies bounded numeric arrays; semantic mesh
verification, OBJ generation and scene validation occur under process limits.

The result retains the original immutable source and its binding. XML and resource
bytes are content-addressed and bound to the requested plan and layer. Parent-side
reply validation checks closed fields, dimensions, bounds, safe resource names,
aggregate byte limits and the full result identity. No preparation worker receives
a filesystem destination, renderer path or cache path.

Source identity is distinct from render identity. Reusing one mesh at two world
poses requires two cold render jobs. Preflight deduplicates identical resolved
placements, scoped by backend/passes, rather than counting a source key once
regardless of placement. Runtime caches must additionally include actual camera,
lighting, renderer and rendering inputs.

The first adapter supports static, untextured PBR plate geometry. Unsupported
UV/texture inputs, animated bindings and proxy recipes fail explicitly. This
does not authorize dropping maps or changing an approved drawing's materials.
Static mixed emission and renderer-session integration are now provided by
[atomic composition bundles](0105-atomic-composition-bundles.md). Textured/animated
and proxy adapters remain open under SDK-P2-07.
[Tests](../../tests/test_composition_plates.py) verify actual input and failure
behavior and render a prepared scene with only its declared resources.
