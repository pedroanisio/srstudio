---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0031: Shared look, staging and series primitives, one file hash, and readable captions

- Status: accepted; implemented 2026-10-29 (`srstudio.look`, `srstudio.digest`, `srstudio.staging`,
  `srstudio.series`, `CaptionLook.min_last` and `CaptionLook.min_seconds` in `srstudio.native`, the locked
  manifest write in `srstudio.social.publish`; `tests/test_look.py`, `tests/test_digest.py`,
  `tests/test_staging.py`, `tests/test_series.py`, `tests/test_native_orphans.py`, `tests/test_saga_harness.py`,
  `tests/test_social.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); builds on [ADR 0016](0016-episode-helpers-in-the-library.md)
  (reusable helpers live in the library), [ADR 0021](0021-engine-native-features.md) (native captions and
  effects) and [ADR 0025](0025-saga-style.md) (the Saga look pass)

## Context

The operator asked for a review of every video and the whole library, to make sure the library improves with
each style and stays reusable and extensible, and then to fix what it found, test first. The review found:

- **Copied look code.** The Saga look pass (ADR 0025) wrote a measured text wrap, a text-in-a-box helper, a
  shot grade, a blurred far plane and a radial light pool into `saga_sets`. Gloss (ADR 0030) copied them into
  `gloss_sets` with the error class and the id prefix renamed. A fix to one copy would never reach the other.
- **Copied reel engine and episode harness.** `saga_reel` and `gloss_reel` each held the same camera rig (a
  move holding a shake), blackout, coverage and span checks, closing-card crossfades and the caption-and-mix
  ending; `episodes/_saga.py` and `episodes/_gloss.py` each held the same `Reel` dataclass, script builder,
  `word_at` and build function.
- **Six file hashes.** `episode`, `package`, `generated`, `narration`, `outbox` and `social` each defined their
  own SHA-256 of a file; three read the whole file into memory, three streamed it.
- **Unreadable captions.** The engine wraps a caption greedily at `maxCharsPerLine`, so "They are shooting into
  it!" shows "it!" alone on its second line, and splitting a long take greedily into cues left a last cue of
  one word ("is?"), which the engine's legibility check reported as shown for less than its 0.8333 s minimum.
- **A delivery race.** `social.publish` read `delivery.json`, rendered covers for seconds, then wrote back the
  entries of that early read: two `deliver --only` runs at once dropped each other's entries.

## Decision

- **`srstudio.look`** holds the picture-finish primitives every style calls with its own numbers: `wrap`
  (raises `look.FitError`, a `ValueError` a style may rename), `label`, `grade`, `depth`, `pool` and `fade`.
  Paint and effect ids are passed in, so a style keeps its own prefix and its scenes stay stable.
- **`srstudio.staging`** is the staged-reel toolkit: `check_cover`, `check_move` and `check_spans` (raising the
  style's own error class), `rig` (a framed group that makes a `Move` holding a shaken group), `blackout`,
  `crossfades` and `close` (the transitions, the engine's captions and the mix, ducked under every line).
- **`srstudio.series`** is the episode harness: a `Series` declares a style's voices, settings, music bed,
  font, encoder output, reel builder and caption look once; a `Reel` subclass names its series; `record` and
  `build` record and build any reel. It carries the LLM banner; `srstudio.takes` owns the verification.
- **Saga is ported** onto all three; `saga_sets.wrap` stays as a thin wrapper that refuses with `SagaError`.
- **Gloss is ported** onto all three once its reels were delivered: `gloss_sets` draws with `look`
  (`gloss_sets.wrap` refuses with `GlossError`), `gloss_reel` stages with `staging` and `episodes/_gloss.py` is a
  `Series` in the house caption look, a reel naming `captions=gloss_reel.LOOK` (G7 on). Two opt-in arguments
  serve it: `staging.rig(name=)` names the camera frame (`gloss-<take>-angle`, which `srstudio.craft` counts the
  moves of) without spending a serial id, and `series.line(heard=)` carries a transcript the operator accepted.
  The grade stays on each shot's world group, so the board and the corner badge stay crisp, and the music still
  hushes through the pauses (`gloss_reel.hush`).
- **`srstudio.digest.sha256`** streams a file in 1 MiB blocks; the other modules' hashes are that function under
  their old names (`outbox` keeps its own until another session's edit to it lands).
- **Readable captions, opt-in per `CaptionLook`:**
  - `min_last` is the fewest words a cue's last line may hold. With more than 1, an orphaned cue is split in two
    where both halves fit without an orphan and the second holds at least `min_last` words: after a word that
    ends a clause (`.,!?;:…`) if one can, else where the halves balance, the longer half first on a tie.
  - `min_seconds` is the shortest a cue is shown: it is held into the silence after it, never into the next
    cue or past its own take, and a split whose half could not be shown that long is not made.
  - When a long take is split greedily into cues and its last cue is too small (fewer than `min_last` words,
    or too short to be shown `min_seconds`), the last two cues are cut afresh at the best readable split.
  - A cue no readable split frees of its orphan is kept whole: a lone last word is easier to read than a
    caption flashed too briefly. A cue without word timings that needs a split is refused with `NativeError`.
  - The Saga series look is `CaptionLook(min_last=2, min_seconds=0.84)`.
- **`social.publish` writes the manifest under an exclusive lock** (`delivery.json.lock`) and, for an `only`
  delivery, re-reads it there and replaces only the entries it delivered.

## Consequences

- A new style draws its finish with `look`, stages with `staging` and declares a `Series`; it adds only what is
  its own, and a fix to the shared code reaches every style that uses it.
- Proof of no change to shipped work from the ports: each of the 12 Saga projects was rebuilt before and after
  each port, and the scene XML of every one whose episode script did not change in between was byte-identical.
  The Gloss port was proved the same way: G1–G7 rebuilt from their recordings before it and after each of its
  steps, and the scene XML, `ig.txt` and `qa/sdk-validation.json` of all seven were byte-identical to the
  delivered projects.
- The Saga caption look re-timed captions of S1–S7, so they were rebuilt, re-encoded and re-delivered. Their
  encodes report no caption legibility warning; `instagram_posts.py check` reports none of them drifted.
- The engine still reports caption contrast below 4.5:1 on some Saga frames (down to 1.00:1). Its measure
  (`contrast_of` in scene-render `sr-gpu/src/render_access.rs`) averages every pixel the caption changed, so the
  white fill and the dark outline of the caption cancel over a mid-tone backdrop; the frames read clearly. This
  is an engine measurement limit for outlined text, not a caption defect, and is left to the engine.
- `min_last`, `min_seconds` and the tail re-cut are opt-in: the house look (`CAPTION_LOOK`) is unchanged, so the
  captions of every other delivered video rebuild byte-identical.

## Rejected alternatives

- **A base class for style set or reel modules.** Styles differ in what they draw, not in how they finish or
  stage it; plain functions with explicit ids and error classes compose with every style without a hierarchy.
- **Readable captions by default.** The better default, but it re-times every delivered video's captions; the
  library does not change a shipped default.
- **Refusing an orphan no split can free.** It forced a rewording of recorded lines (new takes, new cost) for a
  cosmetic defect; keeping the cue whole is readable.
- **Always re-cutting a long take's last two cues.** It replaced clean clause breaks ("…battle cube." / "From
  the inside.") with mid-phrase ones; only a last cue too small to read is re-cut.
- **Locking the whole delivery.** It would serialise cover rendering across sessions; the lock covers only the
  manifest's read-merge-write.
- **Porting Gloss in the same change.** Gloss's modules are still being changed by the session delivering it;
  it moves onto `look`, `staging` and `series` once its episodes are delivered.
