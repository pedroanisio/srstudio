---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0021: New episodes use the engine's own captions, transitions, effects and text animators

- Status: accepted and implemented, 2026-10-28 (`srstudio.native`, `Episode.native_captions`, `Canvas.apply`,
  `Canvas.animate_text`, `Canvas.effect` merged with the Stick car's, `docs/engine-features.json`,
  `tests/test_native.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The 18 scenes the library had built used 31 of the 162 elements of the sr-core.scene schema (release 1.7.2). The
library drew by hand several things that scene-render 0.8.0 does itself:

- **Captions** had five implementations (`graphics.captions`, `ink.caption`, `toon.captions`, `stick.captions`,
  `Episode.captions`). Three episodes paged the words with `subtitles.chunk_words`. Each one drew a text layer per
  page, and none of them could sing a word as it was said or write a subtitle file.
- **Every cut was hard.** The schema has `<transition>` between shots of a `<sequence>`.
- **Text cards popped in** through scale keys (`Canvas.pop_in`). The schema has `<textAnimator>` presets.
- **Effects** existed only in the Stick car, through a `Canvas.effect` added while this work was in progress.

A probe scene showed what the engine does with these elements:

- A `karaoke` track renders word by word.
- A `whip-pan` and a `crossfade` blend the two shots.
- `drop-shadow` and `pop` render.
- Encoding with `mode="both"` writes the video and `<output stem>.<track>.<language>.vtt`.
- The engine's safe-area check (SA01) measures the drawn caption, not its `width` attribute.
- The engine wraps lines by `maxCharsPerLine` only, so a line can be wider than the box.

## Decision

1. **`srstudio.native.caption_track`** writes `<captions><captionTrack>` with a `<cue>` per line and a `<word>` per
   spoken word, plus two text styles (the face and the sung word). Its inputs:
   - cues from `cues_from_takes` (the words of the takes, moved onto the scene clock) or from `cues_from_phrases`;
   - a `CaptionLook`, the house look by default: white, an 8 px outline drawn outside, the sung word gold,
     `karaoke`, 24 characters a line.

   With a safe area, the track is centred on the region and its last line sits on the region's bottom edge.
   `mode` burns the track into the output, writes a sidecar, or both. `Episode.native_captions` passes the
   episode's takes, safe area, output, language and font.
2. **`srstudio.native.transition`** puts a `<transition>` between two neighbouring shots of a sequence.
3. **`Canvas.effect`, `Canvas.apply` and `Canvas.animate_text`** declare effects, add them to nodes and put
   presets on text layers. The two `Canvas.effect` definitions are now one:
   - it keeps the Stick car's signature;
   - asking for an existing name with the same settings returns it;
   - asking for an existing name with other settings is refused.
4. **The checks the schema cannot express are code**, and each one raises `NativeError` before anything is
   written:
   - cues in time and in order, without overlaps;
   - words inside their cue and in order;
   - a caption block that fits the safe area;
   - every wrapped line measured with the caption font against the room it has (`fonts.text_width`);
   - a transition only between neighbouring shots, and no longer than either of them.

   The SDK already refuses an unknown preset, type or attribute (`SchemaValueError`), so those are not repeated.
5. **`docs/engine-features.json`** records each feature:
   - adopted or hand-rolled;
   - the library API that writes it;
   - the test that verifies it.

   A test fails when a named API or test is missing.

Everything is opt-in: no shipped episode, style or default changes.

## Rejected alternatives

- **Switching the shipped episodes to native captions.** Every delivered episode would render differently on its
  next rebuild, and the Ink and Stick packages would no longer match their shipped scenes.
- **Trusting the engine's wrapping.** The engine breaks lines by character count, so a line of wide letters
  overflows the frame. Measuring with the font refuses that before the render. The uppercase house look at 24
  characters measured 844 px against 840 px; at 18 characters it fits.
- **A sidecar of our own (`subtitles.write_srt`).** The engine writes the WebVTT from the same cues it burns, so
  the two cannot disagree.
- **The engine's `<camera>` and `<shake>` for 2D moves.** They apply to 3D content. `srstudio.camera` keeps its
  group-key moves.

## Consequences

- A new episode calls `ep.native_captions()` instead of drawing caption pages, and gets word-by-word captions and
  an optional `.vtt` for accessibility.
- An uppercase look needs `max_chars` of about 18 at 53 px. The font check names the line that does not fit.
- Words that run past their take are refused, not clamped. The synthetic `router_takes_data` fixture has such
  words. The timelines of *The Router*, *Screen Share* and *Repeat After Me* pass.
- Only `karaoke` captions and the `crossfade` transition are checked by pixels in the suite.
  - `drop-shadow`, the `pop` animator and the uppercase karaoke track pass the engine's validation.
  - Other presets and types are checked only against the schema.
