---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0177: Compile a scene timeline under one render budget

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

A timeline cannot be emitted by independently compiling every sampled static
scene: that resets render budgets, includes hidden layers and loses source
boundaries. `scene_motion.compile_timeline` and `emit_timeline` consume the
aggregate plan and preserve its half-open view/source intervals.

Compilation recomputes the timeline and verifies vector XML and every raster
snapshot for every unique view, including the terminal pose. Preparation streams
one placement at a time and retains identity receipts. Execution prepares the
needed placements again and checks those receipts. Retaining every prepared
mesh for the entire movie was rejected because it expands geometry storage with
clip length. Rendering during first-pass preparation was rejected because a
later invalid hidden snapshot would already have mutated the cache.

Actual raw render keys and declarations must fit the planned aggregate work.
All warm cache entries are validated before any cold job. Existing bounded
renderer sessions count attempts, label work and failures across the entire
clip and any enclosing session. The existing cache identity and atomic directory
publisher are shared with static bundles. Valid individual cache entries may
survive later failure; the output bundle is published only when complete.

A dedicated bounded assembly worker receives the original typed inputs and
recomputes the schedule. It verifies closed image/placement tables, PNG identity
and dimensions, scoped vector IDs and paint references, node/byte bounds and
the final scene schema. Original vector source clocks remain inside outer held
view intervals. Final image identity is independent of raw render identity;
several palette/grain snapshots may reuse the same raw light/ID passes.

Timeline IPC permits 32 MiB to carry both bounded original raster inputs and
verified output images. Existing composition IPC stays at 16 MiB. The 8 MiB
source/input/output limits and hard worker memory/deadline controls remain in
force. The protocol contains no executable callbacks or caller-selected imports.

The [executable guide](../composition-preflight.md#emit-a-scene-timeline),
[emission tests](../../tests/test_scene_timeline_emission.py) and
[protocol tests](../../tests/test_scene_timeline_protocol.py) cover this adapter.
It does not replace the full animated DRAWING adoption proof or certify
biomechanics, emotion coordination or perceptual continuity.
