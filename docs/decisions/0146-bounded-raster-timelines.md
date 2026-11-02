---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0146: Preserve source clocks in bounded raster timelines

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

Animation can be supplied as immutable geometry and appearance snapshots.
`RasterSequence` owns finite source duration and strictly increasing snapshot
times beginning at zero. Each `RasterFrame` holds a complete plate or proxy
source until its successor. The adapter makes replacement timing explicit;
it does not invent interpolation, easing or physical continuity.

The binding retains the original animated duration, anchors, bounds, node and
memory declarations. Preparation verifies all snapshots under that same plan.
Clearing the binding's duration to reuse a static plan was rejected because it
invalidates animated anchors and disconnects preparation from contact clocks.
Instead, sequence preparation selects each frame's declared raw jobs and reuses
the verified plate core or the proxy core's explicit sequence scope. Bare frame
assets cannot bypass sequence verification at the bundle boundary.

`raster_jobs` derives unique raw work, including proxy light/ID passes and
printed-label dependencies. The complete source must fit input, preparation,
node and memory bounds. Every snapshot is checked before cache access, including
ones outside the selected clip. Only visible held intervals require rendering.
Content-addressed jobs deduplicate repeated snapshots and preserve warm reuse
across source offsets and rates. Proxy sequences keep one oversampling factor
so a raw work key cannot conceal different sampling resolutions.

`raster_schedule` uses rational arithmetic over declared decimal times, then
requires representable positive scene intervals. Emission flattens source time
into explicit half-open visibility groups once. It neither resets the source
clock at cuts nor relies on accumulated sequence durations. The engine's actual
visibility evaluation and rendered frames verify the boundary convention.
Repeated images use a bounded image table with typed, complete references.

Rejected alternatives include live builder callbacks in workers, validating
only visible frames, implicit mesh interpolation, clearing animated binding
metadata, and rendering every source frame for a small cut. These respectively
hide executable behavior, allow invalid hidden inputs, invent motion semantics,
lose the original contracts, and spend unnecessary renderer work.

The scene camera, lights and parent transforms remain static. Snapshots can bake
object motion and appearance changes in source space. Shared-light vector
picture adapters, animated view/light/parent tracks, cross-layer receivers and
operator approval of animated style quality remain open. The
[guide](../composition-preflight.md#animate-held-raster-snapshots) and
[tests](../../tests/test_composition_sequences.py) define the supported boundary.
