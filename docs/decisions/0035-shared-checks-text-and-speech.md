---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0035: One home for the checks, text helpers and speech helpers every style copied

- Status: accepted; implemented 2026-10-29 (`srstudio.checks`, `Canvas.require_font`, `look.text`,
  `lipsync.talk`, `lipsync.check_track`, `rig.check_place`, `rig.blinks`; `tests/test_checks.py`,
  `tests/test_canvas_and_registry.py`, `tests/test_look.py`, `tests/test_lipsync.py`, `tests/test_rig.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Each new style copied the previous style's input checks, font guard, text helper and speech helpers, so the same
code existed in several modules with small differences. Some differences were deliberate:

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
- **`Canvas.require_font(what, error=ValueError)` is the font guard.** It returns the caption font asset, or
  raises `error("this canvas has no caption font; <what>")`. The 14 guards in the Stick, Stick sets, Toon, Collage
  and prop modules call it with their own `what`, so each refusal reads as before, and Collage keeps
  `CollageError`. `Canvas.text` and `native` keep their own guards, whose wording points at `EpisodeSpec.font`.
- **`look.text` sets a text in an asset of its own.** It takes `weight`, `align`, `lines` (balance over at most
  that many lines), `wrap`, `line_height`, `overflow` and the id prefixes of its asset and its layer, and it sets
  only the options given. It replaces the `_label` and `_text` copies in `stick`, `stick_car`, the Stick sets
  (gym, airport, school, shop) and the Ink captcha, phone, doorbell and vacuum. Each module keeps its defaults as a
  `functools.partial`, or as a two-line wrapper where it rounds the box to whole pixels. `look.label`, which sets
  a line through `Canvas.text` (one id, a `-layer` suffix, line height 1.12), is unchanged. One function could
  not serve both, because the two write different ids and attributes, and published scenes hold both.
- **The lit cast's speech and rig helpers live in `lipsync` and `rig`.** `lipsync.VISEMES`, `lipsync.talk` (one
  state per change of viseme, closed at the end of the take) and `lipsync.check_track` (seconds that rise from 0
  and fall before an end, in known states, refused in the caller's error and words) replace the identical copies
  in `saga` and `gloss`. `rig.check_place` (a scale and a shot above 0) and `rig.blinks` replace their
  `_check_place` and `_blinks` too. The styles' differences are parameters: the Saga blink is every 3.1 s from
  0.7 s and keys nothing on a shot too short to blink, while the Gloss blink is every 2.9 s from 0.6 s and holds
  the eyes open with one key. `saga.talk`, `saga.check_talk`, `gloss.talk`, `gloss.check_talk` and
  `gloss.check_track` keep their signatures and their messages ("after" in Saga, "rise after" in Gloss).

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
