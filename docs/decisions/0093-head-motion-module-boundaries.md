---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0093: Head-motion implementation boundaries

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Keep `srstudio.head_motion` as the public API and move its implementations into
five cohesive internal modules. The public module re-exports the same objects;
it does not wrap calls or implement a second sampler.

| Module | Responsibility | Dependencies within head motion |
| --- | --- | --- |
| `_head_channels` | Channel and spring records, sampling, baking, extrema and shared typed failure helpers | None; uses `_curves` for interpolation math |
| `_head_types` | Style and plan records, settings, gaze validation and rig envelopes | Channels |
| `_head_noise` | Stateless seeded hash and noise | Shared failure helpers in channels |
| `_head_speech` | Character alignment, measured loudness, stress, accents and nod/listening cues | Types, noise and shared failure helpers |
| `_head_planner` | Assemble speech, facing, gaze, breath and idle keys into a bounded plan | Channels, types, speech and noise |

Dependencies point toward the lower layers. Internal modules never import the
public facade. Curve math remains in `_curves`; planning does not acquire its
own easing, spring response or spline implementation. The existing 64-entry
sampling caches remain owned by channel mechanics, and the one-entry stress
lexicon cache remains owned by speech analysis.

Public exports, signatures and type hints remain compatible. Public classes and
functions retain `srstudio.head_motion` as their runtime module identity for
pickles and existing class-qualified error codes. Source navigation should use
the implementation table above; that stable identity does not identify a moved
class's physical source file. Existing internal consumers retain aliases for
`Key`, `SPRING_RUN`, `_CURVES`, `_bake_spring`, `_sample_spring` and
`_channel_bounds`. These aliases do not make private helpers supported public API.

## Compatibility evidence

The committed fixture in `tests/data/head-motion-compatibility.json` was captured
from `fdae9a22` before extraction. It covers every supported curve, short carried
springs with under/critical/over damping, long carried springs, empty and held
channels, keys and cut boundaries, and composed speech/listening/facing/idle.
It records numeric samples, emitted scene XML hashes, public signatures and nine
protocol-4 record serializations. Normal tests only read the fixture.

The module-boundary tests first failed because the implementation modules did
not exist. After extraction, their aliases refer to one implementation and the
captured outputs remain unchanged. Existing renderer comparisons independently
check supported curve sampling and shot continuity. No perceptual improvement,
new continuity guarantee or performance improvement follows from moving code.

## Alternatives

- Keeping the single module leaves speech changes coupled to review of numeric
  channel mechanics and obscures which layer owns each invariant.
- Copying a sampler into the planner would allow authored intent and renderer
  emission to disagree. Shared implementations and identity tests prevent that.
- Introducing public import paths for every internal layer would increase the
  compatibility surface without adding authoring capability. The existing public
  path stays stable while maintainers can change internal boundaries.
