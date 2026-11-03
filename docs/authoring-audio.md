---
updated-by: OpenAI Codex (GPT-6)
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
