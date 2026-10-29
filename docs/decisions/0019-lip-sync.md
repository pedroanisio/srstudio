---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0019: Lip sync reads spelling, closes every bilabial, leads the sound and bridges word joins

- Status: accepted and implemented, 2026-10-28 (`srstudio.lipsync`, `PhonemeStyle` fields, `MouthStyle.letters`,
  `sketch.visemes(style=)`, `sketch.record(mouth=)`, `srstudio lipsync`, `tests/test_lipsync.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The library had two lip-sync drivers.

- **Character timestamps** (`soundtrack.phoneme_states`, used by Ink, Stick and the Toon sketches). It read one
  letter at each 1/12 s sample and gave it a pose by itself.
  - A *b*, *m* or *p* shorter than a sample could fall between two samples and never close the mouth.
  - *w* got the teeth pose, the *p* of *ph* closed the mouth, and a silent final *e* opened it.
  - Every space between words closed the mouth, even inside one breath.
  - The mouth changed exactly on the sound, with no lead.
- **Amplitude** (`soundtrack.mouth_states`, used by Cutout and Soft). The RMS picked open, small or rest, but the
  round mouth came from a pattern on the clock (`int(t * 12) % 5 in (0, 3)`), not from the words.

Over the 24 timestamped takes of *The Router* and *Screen Share* (53.5 s), `srstudio lipsync` reports for the
shipped `INK_MOUTH`: 25 of 26 bilabials closed, 67 of 104 joins between words snapped shut, 6.02 pose changes a
second.

## Decision

1. **`srstudio.lipsync`** holds both drivers' reading of the letters (`letter_poses`) and the timestamp sampler
   (`phoneme_states`). `soundtrack.phoneme_states` delegates to it.
2. **Opt-in fields on `PhonemeStyle`**, all on in `SPEECH_MOUTH`:
   - `spelling` reads English spelling;
   - `close_bilabials` forces a closed sample nearest every *b*, *m* and *p*, except in a scream;
   - `lead` shows each sound early (0.04 s, about one frame at 24 fps, as animators lead the track);
   - `min_rest` keeps the previous pose over a pause between letters shorter than 0.12 s.

   Invalid values are refused when the style is made. `SPEECH_MOUTH` scores 26 of 26, 4 of 104 and 5.10 on the
   same takes.
3. **`MouthStyle.letters`** spreads the line's letters in order over the frames where it is voiced. A vowel weighs
   twice a consonant. The letters choose round, rest (a bilabial) or open. The amplitude still chooses open or
   small. Bare `speaking=` spans have no text, so they are refused with `letters`.
4. **`lipsync.score` and `srstudio lipsync`** measure a style over aligned takes, so a later change to the reader is
   judged by numbers.

The defaults are unchanged. `INK_MOUTH` and the sketch style sample exactly as they shipped. A test compares them
with the shipped sampler over 300 seeded takes per style. This keeps the Ink package fidelity and the byte-identical
rebuilds of delivered episodes.

## Rejected alternatives

- **Changing the defaults.** Every delivered Ink, Stick and Toon episode would change on its next rebuild, and the
  Ink package would no longer match its shipped scene.
- **A phoneme dictionary (CMUdict) or a forced aligner.** Either would be more exact, but each adds a dependency
  and data files to do what the provider's character timestamps and a few spelling rules already do for these
  short lines.
- **Smoothing poses with a minimum hold.** It would lower flicker but drop exactly the short bilabials that matter
  most.

## Consequences

- New episodes opt in: `style=SPEECH_MOUTH`, `sketch.record(mouth=SPEECH_MOUTH)` or
  `replace(OFFICE_MOUTH, letters=True)`.
- The Stick rig still hard-codes `INK_MOUTH` in `stick._mouth`. Accepting a style there is the next step.
- The amplitude mapping of letters is a heuristic: it keeps the order of the sounds, not their exact times.
  `srstudio lipsync` scores only the timestamp driver.
