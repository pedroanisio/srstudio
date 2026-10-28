---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0005: One audio call, the audio pipelines in the library, characters as looks

- Status: accepted and implemented, 2026-10-28 (`srstudio.narration`, `srstudio.song`, `Episode.audio`,
  `styles.Mix`, `blob.Look`, `blob.bo`, `blob.home`, `tests/test_narration.py`, `tests/test_song.py`,
  `tests/test_audio.py`, `tests/test_soft.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Four styles had four ways to put sound in an episode: `audio_mix()` for one mixed file, `mix()` plus
`take_audio()` per take, `generated_audio(extra=)` for pinned clips, and hand-written cue code for a narrated
master. Each episode script repeated its style's loudness, true peak and bit depth. The narration steps lived in
two episode scripts and the sung-episode pipeline in `episodes/_song.py`, so none of them was covered by the
library's branch-coverage gate or importable by a new episode. The Soft style had one character and one
location, and its rig drew Pip's sprout, blush and white body inline, so a second character meant copying it.

## Decision

1. **The pipelines are library modules.** `srstudio.narration` holds the narration steps (slots, bounded speed-up,
   placement, conform, the manifest check and `narration_cues`) and raises `NarrationError`. `srstudio.song` holds
   the sung-episode pipeline (`Song`, `Singer`, `Line`, `Effect`, `hear`, `place`, `build`, `main`) and raises
   `SongError`. Episode scripts keep only their data. Both moves were checked by re-running the scripts from the
   ElevenLabs cache and comparing every output file byte for byte.
2. **One call plays the project.** `Episode.audio()` picks the source the project brings (`audio_source`:
   pinned clips, then takes, then one mixed file, else silent) and builds the same mix the explicit call built,
   which `tests/test_audio.py` asserts by comparing scene bytes. A narrated master passes `narration=`. An option
   the source cannot take raises `TypeError` instead of being ignored.
3. **The master is a style value.** `Style.mix` is a `Mix(loudness, true_peak, bit_depth)`: −16 LUFS, −1.5 dBTP,
   24-bit by default, and −14 LUFS with no bit depth for Ink, which is what the Ink episodes already mastered to.
   Explicit `loudness=` and `true_peak=` override it.
4. **A character is the rig in a look.** `blob.blob(..., look=)` draws the rig; a `Look` names the body fill,
   blush, topper, hair and features and checks its colours and name. `pip` is the rig in `PIP`, and its output
   is byte-identical to the inline drawing it replaced (the episode 07 and 08 scene documents did not change).
   `bo` is the rig in `BO`, so every pose and cue works for both.
5. **A second location shares the first one's frame.** `soft-home` draws its sofa on the office chair's 3/4 axes
   at the chair's seat height, so a seated pose fits either. `on_sofa=` seats a character between the seat and
   the near arm, like the other locations' slots. A `lounge` pose rests the hands on the lap, because the seated
   poses type at desk height.

## Rejected alternatives

- **Keep per-style audio calls and document them.** It leaves a new episode to know which call matches its
  project and to repeat the style's master. The explicit calls stay for mixes one call does not cover.
- **Infer the source from the style instead of the project.** A Cel episode is silent or narrated, depending on
  whether `narration.json` is there, so the style alone cannot decide.
- **Subclass a character per look.** The looks differ only in drawers and colours; data on one rig keeps the
  pose sheet single and lets a test compare the two characters directly.
- **Draw the home in its own perspective.** Every seated pose would need a second fit, and characters moving
  between the two locations would change size.

## Consequences

- An option an episode used to pass that the new call does not take is an error, so a mismatch shows at build
  time.
- The other episodes build through `ep.audio()`; the printer recreation keeps the explicit calls because its
  beep asset has no hash to pin, and mushroom training's narrated build moves to `ep.audio(narration=)` with its
  own change.
