---
generated-by: Claude Fable 5.1 (claude-fable-5-1) and Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0020: A lip-synced Toon cast: viseme tracks from the recording, polish fields on the Look, a bear and a rabbit

- Status: accepted and implemented, 2026-10-28 (`toon_cast.BEAR`/`RABBIT`, `Look` polish fields, `VISEMES`,
  `viseme_keys`, `blink_times`, `figure_layers`, `mouths=`; `sketch.visemes`, `extend_track`, `load_mouths`,
  `write_voiced(mouths=)`, `drawer_extras`; `toon_props.board_text` wrapping on screen; `_toon_sketch` reading
  `voiced/mouths.json` and `record_episode(mouth=)`; `episodes/quick_question*.py`; their tests)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Fable 5.1 and Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); follows [ADR 0014](0014-toon-brush-characters.md) and
  [ADR 0015](0015-toon-sketches.md); the letter reading it can opt into is [ADR 0019](0019-lip-sync.md)

## Context

The operator asked for two more Toon characters, more polished than the dog and the frog, and with lip sync. In the
Toon sketches a character's mouth was one of the nine expression mouths of its pose. It held still through a whole
line, so a speaking character looked the same as a listening one.

The recording run already had what lip sync needs. Every ElevenLabs take returns character timestamps
(`voice.Alignment`), and `soundtrack.phoneme_states` already turns them into closed, open, round, teeth and shout
samples for Ink and Stick.

## Decision

1. **Visemes are a separate vocabulary from expressions.** `toon_cast.VISEMES` is closed, open, round and teeth
   (shout maps to open). "Closed" draws the pose's own mouth. A character that stops talking keeps its smirk or its
   dropped jaw, and the nine expression mouths stay what the poses choose.
2. **The track is recorded, typed and stored.** `sketch.record` samples each kept take at `VISEME_RATE` (12 Hz,
   the Toon reading `MOUTH_STYLE`). It places the samples at the take's project start and appends them to the
   character's track with `extend_track`, which refuses overlapping takes. The run writes `voiced/mouths.json`
   (`{end, mouths: {character: [[second, viseme], …]}}`). `load_mouths` parses it into exact keys, known lip-synced
   characters, known visemes and strictly rising seconds within the project. The voiced build refuses a track whose
   end differs from `voiced/beats.json`.
3. **The drawing keys layers, it does not redraw.** For each pose run `figure` draws one group per viseme heard in
   that run and keys its opacity on the composition clock (`viseme_keys`). A run with no speech draws the plain
   mouth with no keys. `figure_layers` splits the figure into the layers under the mouth, the mouth and the layers
   over it (the rabbit's teeth, the paws, stickers), so the typing frames swap only the under layers.
4. **Polish is opt-in per Look.** `brows` (lift per eye kind: up for a shock, a frown for narrow), `shine` (a
   highlight per pupil), `blush`, `ear_inner`, `teeth`, `whiskers` and `blink` (seconds between blinks, a lid over
   each eye for `BLINK_HOLD`) default off. The dog and frog draw exactly as before.
5. **A new episode may opt into the better letter reading.** `record_episode(mouth=)` passes a `PhonemeStyle` to
   `sketch.record`. *Quick Question* uses the Toon reading plus ADR 0019's spelling, closed bilabials, lead and
   bridged joins. The default stays `MOUTH_STYLE`, so re-recording *The Report* and *Logo Bigger* from the cache
   reproduced their manifests byte for byte and only added their tracks.
6. **Board text wraps inside the part of the board on screen.** The board runs off the right edge of the frame,
   and a large size cut its last word off. `board_text` now wraps within `BOARD_SEEN`.

## Rejected alternatives

- **Adding viseme mouths to `toon.MOUTHS`.** Poses would have to carry speech, and every beat would need a mouth per
  sound. Speech and expression change at different rates and come from different sources.
- **Redrawing the whole figure per viseme.** The figures have about 40 layers. Keying four small mouth groups per run
  keeps the scenes near their previous size (1,503 shapes for *Quick Question*).
- **Amplitude-driven mouths (`soundtrack.mouth_states`).** The sketches have the exact letters and their times, so
  the round and teeth shapes can follow the words instead of the loudness.
- **Lip sync for the traced cat.** Its mouths are traced from the reference reel; it takes neither stickers nor a
  track, and `drawer_extras` refuses both.

## Consequences

- Every brush-drawn character in a voiced sketch moves its mouth on its own words. The three Toon sketches were
  rebuilt with their tracks and re-encoded with no findings.
- A track depends on the recording. Re-running the recording rewrites `voiced/mouths.json` together with the beats,
  and the build refuses a stale pair.
- Speech-to-text must hear each line exactly. "standup" was heard as "stand up", so the line is written
  "stand-up"; the word check splits both the same way.
