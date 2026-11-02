---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0176: Budget the complete sampled scene timeline

- Status: accepted (2026-11-02)
- Back to the [library README](../../README.md)

Individually affordable camera/light/parent samples can exceed a clip's total
render budget. `scene_motion.plan_scene` creates a single immutable timeline
with a deterministic schedule and aggregate conservative work estimate before
execution. It requires complete immutable raster inputs so source clocks and
visible raw jobs can be resolved without guessing their cadence.

The schedule combines rational frame times, authored motion keys, layer windows
and mapped source snapshots. Every interval holds one sampled scene view.
Original source clocks remain attached to all samples, while explicit off-grid
cuts become interval boundaries. Identical adjacent selections coalesce. The
terminal view is validated separately and never becomes an extra output frame.
Only changing numeric segments expand onto the output frame grid. Long held
clips retain their complete output-frame costs without constructing redundant
scene samples or exhausting the sampled-interval limit.

Raw job identity includes source content, sampled camera/light state, physical
scale, parent pose, dimensions and seed. Proxy light and part-ID passes use their
actual separate lighting states. Counting every frame independently was rejected
because held views and repeated cuts can reuse work; counting one source job
for the whole clip was rejected because changed views require new renders.

Resolved pose numbers are encoded as floating point for work identity. An
identity parent can change an origin from integer zero to floating-point zero
without changing prepared XML or geometry buffers. Tests compare actual
prepared renderer identities before allowing those placements to share a job.
Static composition preflight uses the same pose key.

The planner bounds combined intervals, record visits, source buffers, raw jobs,
engine attempts, sampling work, nodes, contact proofs and retained metadata/image
storage. View revalidation and all source snapshots count toward the expansion
bound. Retained scene records require their own storage allowance even when a
host declares tiny drawing-node counts. No cache or renderer is consulted.

The base manifest still passes its existing static preflight; selecting a small
source window does not bypass those initial declaration budgets. Actual mesh
bounds, payload geometry and resource sizes remain preparation responsibilities.
The timeline is an input to the next emission adapter, not a rendered clip or
style approval. [The guide](../composition-preflight.md#plan-a-scene-timeline)
and [tests](../../tests/test_scene_timeline.py) define this planning boundary.
