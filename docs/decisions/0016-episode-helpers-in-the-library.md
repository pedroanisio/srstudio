---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0016: Episode helpers that were copied between scripts now live in the library

- Status: accepted and implemented, 2026-10-28 (`blob.cue`, `blob.settle`, `layout.find_engine`,
  `Episode.check_overlays`, `Episode.audio(duck=)`, `srstudio.interview`, `tests/test_soft_cues.py`,
  `tests/test_layout.py`, `tests/test_audio.py`, `tests/test_interview.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

A review of every episode script for reuse found the same code pasted between episodes:

- **Soft cues in pixels and eased-move settling.** Three copies, in `camera_off.py`, `focus_mode.py` and
  `off_and_on.py`. Each placed a `Cue` at a pixel spot divided by the cast's scale. Each also capped every ease so a
  move never starts before the previous pose has landed. Without that cap, the rig refuses the performance.
- **Finding the engine.** Eight copies of `$SRSTUDIO_ENGINE`, then `scene-render` on the `PATH`. They had diverging
  error messages. Three episodes built on this a strict overlay check against the safe area.
- **Ducking the music under the spoken lines.** `off_and_on.py` listed its spoken track ids by hand. Camera Off had
  no ducking at all, so its two spoken lines played about 6–7 dB under its music. Measured on the assets: the lines
  at -23 and -21 dB mean, the music under them at -16.5 and -15.2 dB.
- **Shot spans from the cuts.** `off_and_on.py` rewrote `Timeline.shots` instead of calling it.
- **The interview audio pipeline.** `upside_down_audio.py` was a copy of `five_years_audio.py`: the same
  declarations, resolve, speech check, trimming, levelling, room tone, font and `dialogue.json`. Only the script,
  the effects, the schedule and the cuts differed. Neither copy refused a near-silent take, as `song` does, or a
  schedule that overlapped two lines.

## Decision

1. **`blob.cue(time, pose, spot=None, *, scale, ease, **kw)`** places a cue at a spot in output pixels. A cue at 0
   never eases. A scale that cannot map pixels is a `BlobError`. Episodes bind their defaults with
   `functools.partial`.
2. **`blob.settle(cues, fps)`** orders the cues and caps each ease to the time since the previous pose landed. After
   an overshoot, that time counts from one drawing later. Equal cue times and a non-positive `fps` are refused.
3. **`layout.find_engine(explicit=None)`** is the one engine lookup: the explicit path, then `$SRSTUDIO_ENGINE`, then
   the `PATH`. A missing or nonexistent engine is a `LayoutError` that says what to supply. `song.main` and the two
   interview audio scripts use it.
4. **`Episode.check_overlays(document, roots, engine=None)`** runs the strict overlay check with that engine.
5. **`Episode.audio(duck=dB)`** lowers every `music` track by `duck` dB while any `dialogue` track plays. It takes a
   negative number. It is refused for a source with nothing to duck, and when the mix has no music or no spoken
   track. Sung lines live inside the music track and are not `dialogue` tracks, so they are never ducked against
   themselves.
6. **`srstudio.interview`** is the interview pipeline, as `srstudio.song` is the Soft one.
   - The episode file declares an `Interview` (voices as `song.Singer`, `Spoken` lines, `Sound` effects with an
     optional seed). The `Interview` is checked when made.
   - The episode file supplies a `schedule(line lengths, effect lengths) -> Schedule`. `place` refuses a schedule
     with a wrong line count, overlapping lines, a missing or unknown effect, a negative start, or an effect past
     the end card. It also refuses a take that needs more than `song.MAX_GAIN` to level.
   - The episode file supplies an `extra(Timing)` for its beats and cuts.
   - Rerun offline from the provider cache, Upside Down reproduces every output byte for byte. In Five Years only
     the reaction and end-card times move, by 5 × 10⁻⁷ s: the library takes them from the exact end of the last
     line, where the old script took the rounded record. No frame changes.

The five episodes that moved to helpers 1–5 were rebuilt from their unchanged `dialogue.json` into a scratch copy
and compared byte for byte. Off and On, Focus Mode, Five Years and Upside Down rebuild byte-identical. Camera Off changed on purpose: it now ducks. Its
music is 4 dB lower plus 8 dB of ducking under the spoken lines, so it was re-encoded and its post cover redelivered.

## Rejected alternatives

- **Settling inside the rig.** If `blob` capped eases silently, a cue whose ease could not fit would be changed
  instead of refused. That would hide mistakes in hand-written performances. `settle` is an explicit step.
- **A duck given per track in `extra`.** The caller would have to know the generated track ids. That is the coupling
  `off_and_on.py` had to hand-build.
- **A shared episode helper module (`episodes/_common.py`).** Library users outside this repository would not get
  it, and it has no tests of its own.

## Consequences

- A new Soft episode needs no copy of `cue` or `settle`, and a new episode with an overlay check needs no engine
  lookup.
- `episodes/instagram_posts.py` still has its own engine lookup. It belongs to the thumbnail and publish work
  ([ADR 0013](0013-designed-thumbnails-and-publish-gate.md)) and can move to `find_engine` with it.
