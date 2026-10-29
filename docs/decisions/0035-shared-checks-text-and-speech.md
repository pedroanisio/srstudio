---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0035: One home for the input checks every style copied

- Status: accepted; implemented 2026-10-29 (`srstudio.checks`; `tests/test_checks.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Each new style copied the previous style's input checks, so the same check existed in several modules with
small differences. Some differences were deliberate:

- A Saga or Gloss set is drawn for more than 0 s, while a Toon set may be a still (an end of 0).
- Saga set spans are cut at the set's end, while staging and Gloss spans must end inside the shot.
- Toon spans must be in order and must not overlap.

Others were accidents of how each copy was written:

- `math.isfinite(True)` is true, so most copies took `True` as one second.
- The Ink captcha and phone tested `at < 0`, which is false for NaN, so they took NaN and infinity as times.
- The hologram's rising check started from `-1.0` and took a negative start, although its message says the
  start falls in `0..end`.

## Decision

- **`srstudio.checks` decides what each kind of input accepts.** A number is a finite `int` or `float` and never
  a `bool`. The module holds `positive`, `non_negative`, `second` (from 0, and before an `end` when one is given),
  `spans` and `rising`.
- **The caller keeps its error and its words.** Every check takes the caller's error class and message, so
  `SagaError("a set is drawn for more than 0 s, got 0")` and every other refusal read as they did. The messages of
  `spans` and `rising` are callables, because they name the span or the index that failed.
- **Deliberate differences are explicit.** `positive` and `non_negative` are two checks, not one with a flag.
  `spans` takes `within=` (refuse a span past the end), `clamp=` (cut it at the end) and `ordered=` (refuse an
  overlap), and a caller passes the ones it means.
- **Accidental acceptance is refused.** A `bool`, NaN or infinity is no longer a second, an end or a span bound.
  A negative hologram start is no longer accepted.
- **Adopted by** `staging.check_spans`, the `saga_sets`, `toon_sets` and `gloss` end, second and span checks, the
  `stick_flat` drop time, the Ink captcha and phone times, and the Saga hologram's panel starts. The Gloss set
  checks in `gloss_sets` adopt `checks.rising` after this change merges.

## Rejected alternatives

- **One `spans` check with a single meaning.** If it were bounded, it would refuse the Saga spans that run past
  a set's end, which `saga_sets` documents as allowed. If it were unordered, it would accept overlapping Toon spans.
- **Shared messages.** A message is part of a style's contract with its tests and its authors. A shared wording
  would change every refusal, and nothing would gain from it.
- **Predicates only (`is_span(a, b)`), with each caller raising.** The raise and the message construction would
  stay copied in every caller, and so would the chance that one caller tests a different condition.

## Consequences

- All 81 episode and package projects rebuild byte-identical to the build before this change, each with the
  flags it was published with. The tightened checks refuse only values that no project carries.
- A new style imports `checks` instead of copying the last style's validators.
- The order of refusals for a hologram changed: every start is checked before any tone or face, so a hologram
  with two faults now names its first bad start before a bad tone.
