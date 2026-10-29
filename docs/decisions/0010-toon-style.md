---
generated-by: Claude Fable 5.1 (claude-fable-5-1) in Claude Code
---

# ADR 0010: The Toon style — a flat cartoon rig whose expression swaps per cue, pill captions, narrated recreations

- Status: accepted and implemented, 2026-10-28 (`srstudio.toon`, `styles.TOON`, `canvas.PEACH`,
  `fonts.text_width`, `tests/test_toon.py`, `episodes/employee_survey*.py`, `tests/test_employee_survey.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Fable 5.1 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator handed over a screen recording of a the.nope.cat reel ("Anonymous Employee Survey": a blue cartoon
cat at a laptop answers a survey out loud, each phrase in a white pill at the top) and asked for it to be recreated
with the engine, narrated with ElevenLabs, and added to the library as a style. Unlike the Cel and Stick ports there
is no package to rebuild element for element: the only source is 63 s of video, so the look had to be measured
(palette, geometry, caption timing, poses, the sound gaps) and drawn as a rig.

The look is unlike the five styles that exist. One character holds a pose for a whole phrase, then swaps to the
next: heavy near-black ink, flat fills, a wide flat-topped head that runs straight into the body, long whiskers,
eyes that go from wide to half-lidded to squinting to one bulging, a mouth in a few shapes, arms on the desk, at
the keyboard, crossed, or both paws over the mouth. The room is a vertical wall gradient, a window and a chair
back; the desk and the laptop lid are in front. Captions are a bold hand-written italic in a rounded white pill
sized to the text. Portrait, loop at 63.125 s, a voice over the captions with a few typing and camera sounds.

## Decision

1. **Style `TOON`, palette `PEACH`.** Ink `#0b0a0d`, white `#ffffff` (the pills, the eye whites), shade `#5bb7db`
   (the cat) on a `#f8ead9` wall. The caption font is Comic Neue Bold Italic, a Google Font
   (`GoogleFont("Comic Neue", 700, italic=True)`, OFL-1.1, `fontPolicy="pinned"`). 1080×1920 at 24 fps on the
   project clock, `timing="clock"`, `dialogue="script.json"`, `silent=True`: there is no mouth model, a voice is
   narration over the captions. Ids come from `flat_counter("k")`. Parts live in `srstudio.toon`.
2. **Traced drawings in reference pixels** *(revised 2026-10-28; first written as "a rig, not drawings")*. The
   reel is 592×1058 recorded 70 px down a phone screen; `toon.fx`/`toon.fy` map screen pixels to the frame and
   `toon.fh` scales a size without the offset. The first version drew the cat as hand-written path strings measured
   from the recording; the operator judged it not polished enough, and the cat is now traced from the recording's
   own frames into packaged data (`assets/toon/cat.json`, schema `toon-cat/1.0.0`): a body per arm pose, eyes and
   mouths per expression, each a closed cubic path in those pixels, parsed by `toon.parse_art` and drawn flat by
   `toon.flat`. Nine eye kinds (`EYES`), nine mouths (`MOUTHS`) and seven arms (`ARMS`) are the whole vocabulary; a
   pose names one of each. The gaze field is gone: the traced eyes carry their own pupils.
3. **Poses and cues are data, parsed, not trusted.** `toon.parse_poses` and `toon.parse_script` reject unknown
   fields, wrong types, non-finite numbers, a first pose not at 0, out-of-order times, overlapping cues, empty
   captions and names the rig does not have (`ToonDataError`); `toon.runs` refuses a project that ends before its
   last pose. The episode's reel is one data module (`employee_survey_data`): `SENTENCES`, `SEGMENTS`, and typed
   derivations with their own checks (`SurveyDataError`), so the picture and the narration read one source.
4. **One group per pose run; two typing frames swapped on the composition clock** *(revised 2026-10-28)*.
   `toon.cat` draws each run as a group alive from its start to its end. A typing pose holds two traced bodies in
   nested groups with opacity keys on the composition clock (`cv.keys(..., local=False)`, `toon.swap_frames`): the
   engine runs a `timeBase="local"` animation on a group without its own `start` on the composition clock anyway,
   so absolute times are the only ones that fire. `toon.typing_frames` alternates the frames every `TYPE_SWAP`
   while keystrokes are heard (bursts closer than `TYPE_GAP`) and rests on the first frame between bursts, so the
   sound (`foley.taps`) and the picture share their beats. The first version dipped a drawn forearm on each
   keystroke; the operator reported it out of sync, and the clacks now fall only in the quiet windows between the
   placed lines (`typing_bursts(speech=…)`, `SPEECH_MARGIN`), at −2 dB.
5. **Pills are measured from the font file.** `fonts.text_width` sums the `hmtx` advances of a text through the
   font's `cmap` at a size, so `toon.captions` sizes each pill to its text (plus `CAPTION_PAD`, never narrower than
   it is tall) without rendering; the engine keeps the text centred in the same box. A canvas without a font is
   refused.
6. **The narration moves the picture, not the other way round.** `employee_survey_audio.py` records one sentence
   per request at the narrator's own pace, confirms it (alignment spells the line, speech-to-text hears the words,
   the voice id resolves to Brian), cuts the two interrupted sentences at the letter the reference cuts at (from the
   character alignment), places the lines with `plan_relaxed` on the reference's sentence starts, and then
   `place_segments` moves every segment: a spoken one to the word it starts on, a silent one a beat after the line
   before it, bounded by the next spoken one, with a minimum caption hold (`CAPTION_MIN`) that may delay a change at
   most `CAPTION_LAG`. All bounds are constants in ordinary code; the voice decides nothing about termination.
7. **Effects are beds in the manifest.** The typing bed and the camera click are synthesised (`srstudio.foley`),
   listed under `effects` with their onsets, and `employee_survey.py --voice` plays them as effects tracks and
   swaps the typing frames and draws the white flash from the same manifest after checking every SHA-256.

## Rejected alternatives

- **Tagging the episode with Cel or Stick.** Rejected: Cel traces filled drawings under a camera with lettering,
  Stick traces poses at 12 fps with outlined font captions; the reel is a rig of a few swappable parts with a font
  in a pill. A tag would give no reusable parts.
- **A hand-written rig instead of tracing** *(the first decision, reversed 2026-10-28)*. The rig kept the
  vocabulary but not the likeness: the operator judged the drawings not polished enough. The trace keeps the
  vocabulary (every expression is a named entry of the art tables) and takes the drawings from the frames; the
  tracer stays a scratch tool, the art is data the parser checks.
- **Using the reference voice or its timing as the master.** Rejected: the voice is the reference's performer and
  is not cloned (`voice_note`), and a narrator at a natural pace does not land on the reference's times; the
  reference timing is the silent master, the narrated master is placed on the narrator's words.
- **Rendering the caption text to measure it.** Rejected: a measurement by rendering would need the engine in the
  build; the font tables are enough and are tested against a real TrueType file.
- **Local-clock keys for the typing frames.** Rejected after an `eval` of the engine showed them never firing on a nested
  group without its own `start`; the composition clock is what the engine runs.

## Consequences

- A new Toon episode needs a pose list and a caption script; the room, the desk, the cat and the pills come with the
  library, and the data-module pattern (segments naming the words they start on) carries over to any narrated
  recreation.
- The catalog lists the episode under Toon; `srstudio catalog --style toon` lists the four parts of
  `srstudio.toon` and the two coworkers of `srstudio.toon_cast` ([ADR 0014](0014-toon-brush-characters.md)).
- The character, dialogue and captions are adapted from the reference and stay their author's; the narration is an
  ElevenLabs premade voice, the typing and the camera are synthesised, and the sighs of the reference are not
  reproduced.
