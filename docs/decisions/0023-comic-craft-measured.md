---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0023: Camera moves and pauses are built by named helpers and measured from the scene and the render

- Status: accepted and implemented, 2026-10-28 (`camera.crash_zoom`, `camera.SNAP`, `foley.whoosh`,
  `foley.write_whoosh`, `srstudio.craft`, `srstudio craft`; `tests/test_craft.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); the funny-reels skill cites it

## Context

Comedy is also built by the camera and by silence: the crash zoom onto a realisation, the punch-in on the cut, the
wide shot for a physical gag, the pause after a line that wants an answer. The library had the pieces
(`camera.push_in`, `camera.zoom_holds`, `camera.reframe`) but no crash zoom by name, no whoosh to go with one, and
no way to see, after a build, which moves and pauses an episode really has. A pause meant to be awkward that the
music bed fills is not a pause, and nobody could tell without listening frame by frame.

## Decision

- **`camera.crash_zoom`** scales a group on both axes from a hold to `scale` in at most `camera.SNAP` (0.25 s),
  optionally snapping back, and returns the cue time for the sound. Slower than a snap is refused with a pointer to
  `push_in`: a slow crash is a push, and the name should say which one the episode makes.
- **`foley.whoosh`** synthesises a seeded band-passed noise sweep (300 Hz to 3 kHz) that swells into its end, where
  the lens lands; it is deterministic per seed, silent outside its cues, and normalised to `foley.PEAK`.
- **`srstudio.craft` reads the scene, not the script.** A move is a uniform scale change (`scaleX` and `scaleY`
  equal at both keys) of at least 15 % on a group. A hold key or a step under half a frame is a punch-in on the
  cut, a change within `SNAP` a crash, anything slower a push. Groups named as locations, angles, shots or setups
  are the camera; any other group is a gag that grows. Signature marks are ignored.
- **Pauses come from the line timings** (`dialogue.json` phrases, or the `line` items of `narration.json`), as gaps
  of at least 0.8 s, and each is measured on the render with ffmpeg's `volumedetect`; a mean of −35 dB or less is
  quiet, louder is filled. Malformed timings and ffmpeg failures are a typed `CraftError`, never a guess.
- **`srstudio craft PROJECT... --renders DIR [--json]`** prints the report; groups that make the same move together
  fold into one printed line, and the JSON (schema 1.0.0) keeps every group.

## Rejected alternatives

- **Classify by `scaleX` alone.** The first run on the delivered episodes reported a spin (a turn squeezes only the
  width) as 34 crash zooms, and a 1 ms cut as a crash. Both axes and a cut threshold are required.
- **Count pauses from the captions.** Captions are chunked for reading and linger after speech; the takes' own
  timings are the spoken truth.
- **A model judging whether the timing is funny.** ADR 0015 rejected an LLM funny gate; this measures, the operator
  judges.

## Consequences

- Episodes built from SRT subtitles without `dialogue.json` or `narration.json` report no pauses.
- On the delivered episodes the long pauses of the narrated Ink and Soft pieces measure about −20 dB: the score
  plays through them. Whether to duck the bed to silence in a pause is now a measurable choice per episode.
