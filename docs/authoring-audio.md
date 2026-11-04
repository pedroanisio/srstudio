---
updated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# Prepare audio and bind its timeline

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Choose the audio path before drawing the episode. Import `Episode` and `EpisodeSpec`
from `srstudio`, `Timeline` from `srstudio.timeline`, and the relevant modules below.
The episode owns a project root; relative audio paths resolve against that root.
Run commands from the srstudio repository root.

| Input | Placement API | Clock and validation |
| --- | --- | --- |
| One mixed dialogue file | `ep.audio()` | The style selects its input; speech intervals use project seconds. The audio file must exist. |
| Recorded takes | `ep.audio(take=...)` | Takes are contiguous on the project clock. Word and phone timings are relative to each take. |
| Verified generated clips | `ep.generated_audio()` | The `clips` in `dialogue.json` place individual pinned files; a changed file is refused. |
| A narration manifest | `ep.audio(narration=...)` | The manifest supplies checked placement and clip identities; captions must retain those same source timings. |

Use the executable [timeline examples](authoring-timelines.md#timeline-input-formats)
to validate records before constructing the episode. `TimelineError` identifies bad
ranges, ordering and data shapes. Do not replace take-relative word times with
project times: placement adds the take's start.

## Record and verify clips

`srstudio.recording.main(record, doc, argv=..., env=..., options=...)` implements the
shared recording CLI. Its callback receives `(project, environment, ffmpeg, **options)`;
the project is resolved before the callback runs. `options` can add script-specific
flags, but shadowing `project` or `ffmpeg` raises `RecordingError`. Registered episode
recorders run through `srstudio record SLUG PROJECT`; inspect the recorder's help for
its own voice, font and input options.

Import `narration` and `voice` from `srstudio` for the underlying pipeline.
`narration.require_consent` checks the provider environment before cloud work;
missing consent raises `ConsentError`, and the recording CLI reports that refusal
as its exit. `voice` parses provider responses into typed records, checks alignment
spelling and finite ordered timing, and verifies audible audio. Invalid responses
raise `VoiceOutputError` without caching them. Uncached calls have no implicit retry;
cache reads reverify their contents.

### Direct a line

A take in a `takes.Script`, or a `series.line`, can carry a `srstudio.direction.Direction`
([ADR 0234](decisions/0234-voice-direction-per-line.md)). The line's words stay the
captions and what speech-to-text must hear. The direction shapes only the request:

```python
from srstudio.direction import Direction, Pause
from srstudio.series import line
from srstudio.voice import VoiceSettings

line("01b", "leo", "Just... discipline.", hold=0, direction=Direction(
    model="eleven_v4", tags=("sighs",), emphasis=("discipline",),
    pre_hold=0.6, post_hold=0.8, takes=3, pick=1))
line("02", "sam", "Just discipline.", direction=Direction(pauses=(Pause("Just", 0.8),)))  # v2: a break tag
```

- `model`: `eleven_multilingual_v2` (the default), `eleven_v3` or `eleven_v4`.
  `Script.models` or `Series.models` sets one for each voice. v3 and v4 take only
  `VoiceSettings.expressive(stability, similarity_boost)`.
- `tags` (from `AUDIO_TAGS`) and `quality` are performed on v3 and v4. Multilingual v2
  speaks a tag aloud, so it is refused there. `emphasis` writes a word in capitals, on
  v3 and v4 only.
- `pauses` are break tags, on multilingual v2 only. On v3 and v4, cut the line into two
  takes with `pre_hold` or `post_hold`, which are exact silence in the edit.
- `context=True` sends the neighbouring lines as previous and next text. v3 refuses it.
- `takes=N` records N seeds and hears each one. With more than one take, the recording
  stops until `pick=k` names the take to keep. The timeline records every take and the
  pick.

A direction that a line or its model cannot take raises `DirectionError` before any
request is made. A take without a direction is sent exactly as before, with the same
cache key.

### Say an exchange as one dialogue

When two or more voices trade lines, a script can say the run as one Text to Dialogue
request so the turns take their timing from each other:

```python
from srstudio.takes import Exchange, Take

lines = (
    Take("01", "will", "What do you feed him?", 0.0),
    Take("02", "leo", "Dog food. And discipline.", 0.0, direction=Direction(emphasis=("discipline",))),
    Take("03", "will", "Just discipline?", 0.4, direction=Direction(tags=("curious",))),
)
script = Script(..., takes=lines, exchanges=(Exchange("01", "03", takes=2, pick=0),))
```

`srstudio.takes.main` says it with `srstudio.dialogue.say`. Every turn is cut back
into its own take, with its own words for captions and lip sync, and each one is heard
back on its own. Inside an exchange, every take but the last holds 0, and the silence
between turns comes from the dialogue and is recorded as `exchange.gap`. A turn's
direction may carry tags, a quality and emphasis only. Lines outside any exchange are
still one request each, so the choice is made per exchange.

### Measure and gate the delivery

Every recorded take is measured on its own clip, and the numbers go into `timeline.json`
under `prosody`. The words come from speech-to-text, with each word's level and pitch,
plus the words per second, the line's median pitch and its spread (interquartile, in
semitones), and each stressed word's weight (dB over the line's median word) and lift
(semitones over the line's median pitch). When a line has several takes, the "pick one"
message lists them best first: stress weight and lift, then pace. Name the punchline's
word with `Direction(punchline="discipline")`. That marks the line for the gate and asks
nothing different of the provider.

```bash
python -m srstudio.prosody path/to/project   # exit 1 on any finding not waived
```

Key lines are the punchline, the button (the reel's last line) and an answer to a
question. The gate checks:

- pace: at most 3.6 words a second over the reel, and 4.3 on any line;
- timing: the first word by 0.25 s;
- gaps: the reel's median at a change of speaker 0.3 to 0.65 s, no default gap over
  0.7 s, 0.4 to 0.9 s after a question (one up to 1.5 s per reel), and before a
  punchline or the button 1.0 to 1.8 s, flagged under 0.5 s or over 2.0 s;
- the end: 0.3 to 1.2 s after the last word;
- stress: +3 dB and +2 semitones for each stressed word, and on a key line with none
  named, for its loudest word;
- pitch: a key line's spread at least 3.2 semitones, any line's at least 1.5 (flat);
- delivery: the punchline's and the button's lift and weight +1 semitone and +1 dB over
  the reel's other lines;
- holds: the directed `pre_hold` and `post_hold`.

To keep a line off a target, waive it with a reason. Give bounds to move the target,
or leave them out to turn the check off for that take:
`Direction(waive=(Waiver("punch_gap", "the silence is the joke", (1.0, 2.6)),))`. The
reel's pace and its median turn gap are waived on `Script.waive` or `Reel.waive`.

At first delivery, `srstudio.prosody_gate` lists every reel's findings, with each waiver's
reason, in the delivery report. A reel whose `timeline.json` has a `prosody` section is
refused on any finding that is not waived. A reel recorded before the gate has no
section, so it reads "unmeasured" and is never refused.

The generated-asset path uses `srstudio.generated.Generated` and
`scene-render resolve`. The `srstudio-elevenlabs` provider requires
`SRSTUDIO_ALLOW_CLOUD=1`; resolution pins the resulting file's SHA-256. Keep those
pins when binding clips to `Episode.generated_audio()`. A repaired request or a
changed seed is an explicit new generation attempt, not an automatic recovery loop.

A reel cut to a supplied recording, a sound we did not record (a trend audio), uses
`srstudio.supplied` (ADR 0227): `recorder(sketch, sha256, credit, doc)` decodes the
pinned file bit-exact, reads its words once (cached), checks the reading against
the sketch's lines with typed refusals, and writes one whole-file narration item with
the voiced beats, speech and mouths the narrated Toon build reads.

## Keep captions and animation on the audio clock

`narration.words_from_alignment` and `phones_from_alignment` return timings relative
to the trimmed clip. A trim that cuts a word is refused. `schedule` chains takes;
`plan_narration` fits narration to bounded caption windows; `conform` prepares audio
with ffmpeg and verifies its length. `narration_cues` checks the manifest and clip
hashes before placement. Invalid placement or manifest data raises `NarrationError`.

Use [lip sync](authoring-styles.md#lip-sync) for the selected rig's mouth vocabulary
and [acting](authoring-acting.md) to coordinate speech and listening. A cut is a
window of one source performance; it does not restart the speech or facial clock.
Finish with [scene verification](authoring-verification.md) and
[delivery](authoring-delivery.md).

The [Five Years case study](https://github.com/pedroanisio/srstudio-episodes/blob/develop/docs/episode-history.md#new-episodes-with-generated-audio-five-years-06)
retains its original commands and production decisions. Current interface and
failure tests are in [recording](../tests/test_recording.py),
[voice](../tests/test_voice.py), [narration](../tests/test_narration.py),
[generated assets](../tests/test_generated.py) and [audio](../tests/test_audio.py).
