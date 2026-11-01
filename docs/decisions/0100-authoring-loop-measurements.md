---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0100: Authoring-loop measurements

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Provide an opt-in `python -m srstudio.benchmark` command with a versioned fixture
profile. Measure import, full catalog discovery, coordinated acting, moving limb
contact, scene compilation, frame rendering and lit plate caching separately.
Fresh worker processes isolate application cache state for each repeat. The
parent checks phase completeness, work counts and output equivalence before
atomically publishing a private JSON report.

The benchmark fingerprints renderer bytes, Python sources and dependency
versions. It records platform and renderer selectors without claiming to pin
GPU drivers or OS caches. Timing is observed data, never a test pass threshold.
Both the explicit nine-point plan grid and the limb compiler's eight-frame audit
are reported, with different names. Recompilation checks scene bytes; cold,
warm and fresh plate verification compare decoded RGBA pixels.

Add `plates.render_session` to count and bound renderer launches at the shared
plate/print subprocess boundary. Cache hits require no launch. Nested sessions
consume their enclosing budgets and use the smallest timeout; mutable report
fields cannot reset the private attempt count. Context exit restores prior
limits. Existing render signatures and cache identities remain unchanged.

Worker and engine deadlines cap execution. A POSIX process group lets the
parent stop a timed-out worker and its renderer descendants before removing
private files. The CLI reports structured failures and preserves an existing
report on failure. Output cannot replace the renderer itself.

## Alternatives

- One end-to-end timer would mix discovery, planning, compilation and renderer
  cost, obscuring where an authoring accelerator helps.
- Reusing one worker for all repeats would make first-use and warm measurements
  difficult to distinguish.
- Inferring renderer launches from file counts would miss failed launches and
  could count cached files as new work.
- Performance thresholds in correctness tests would turn machine load into
  false regressions. Tests instead assert deterministic outputs and counts.

This change adds measurement and resource controls. It does not claim improved
motion quality, a universal speedup or a representative benchmark for every
rig, scene size or rendering backend. See the [usage guide](../authoring-benchmark.md)
for the pinned workload and comparison boundaries.
