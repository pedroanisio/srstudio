---
generated-by: OpenAI Codex (GPT-6)
---

# 0209: Reuse validated scenes inside timeline view resolution

The hybrid hand adds a baked geometry sequence to the existing car and native
figure. At the authored cadence, repeatedly validating the complete scene for
each raster layer makes the conservative record-visit estimate exceed one
million, even though all sources fit the existing buffer and output limits.

Timeline planning already owns full semantic preflight for every distinct
resolved scene. Its internal plate bridge now consumes that immediate result
without repeating preflight. Backend checks remain in the bridge: supported
projection, layer and lighting, physical units, overscan memory, field of view,
geometry clipping and the engine's up-axis envelope. Source job, memory and
pass checks still run for every resolved view.

The public `plate_view` entry point continues to reproduce preflight and compare
the complete result. There is no caller-controlled validation bypass, global
cache or new trusted wire record. Worker inputs still reconstruct their plans
through the same validated planner. The internal helper is private.

The visit bound accounts for one complete manifest per event, the layer/binding
lookups and eight bounds corners per raster bridge, and the existing per-source
visits. The one-million-record limit is unchanged. Output, render work, source
identity, geometry and memory allowances are unchanged by this refactor.

Tests measure five distinct preflight calls for a five-scene, two-layer
timeline, down from fifteen, and show that public bridge calls still validate.
Forged plan digests and purposes are rejected. Existing timeline budget tests
retain the record-limit refusal. The complete hand candidate plans at 12 fps
without lowering its cadence or increasing core limits.

Rejected alternatives: raising the limit retains redundant work; reducing the
candidate's cadence changes its movement; trusting externally supplied
ValidatedScenePlan instances would weaken a public verification boundary.
