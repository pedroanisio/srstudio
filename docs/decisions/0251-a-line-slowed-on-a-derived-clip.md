---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# 0251 — A line slowed on a derived clip of its take

Date: 2026-11-06

Status: accepted

## Context

The craft bar refuses a line spoken faster than 4.5 words per second over its word span (C7 `pace_span`). On Juno &
Pip ep1 three lines read 4.84 to 5.36 words/s, and the reviewer asked for them to be re-timed by stretching the
existing take, with no new take (Slack 1793967529.705339). `Spoken.speed` cannot do that: it is sent to the voice
provider, so changing it asks for a new take.

## Decision

`Spoken.stretch` (1 to 1.25, default 1) plays the take that many times as long, pitch kept. `interview.stretch`
writes the slowed copy to `assets/stretched/line-N.wav` with ffmpeg's rubberband filter (tempo 1/factor), at the
take's rate and channels, and pins it by its own SHA-256. The take and its pin are never touched. `dialogue.json`
gains a `stretch` record per slowed line (factor, clip, sha256, source take, source_sha256), and the line's phrase
carries `stretch`.

Nothing transcribes the slowed clip. Every reader of word times reads the take's cached transcript slowed by the
factor:

- `interview.stress` lifts the key words on the slowed clip at the take's word times times the factor (`heard=` the
  recorded takes); its record's `source` is the slowed clip.
- `interview.place` trims a slowed line on the slowed clip before any lean, as it trims a stressed line on its take
  (ADR 0241 amendment), so a stress moves no timing.
- `interview.said` scales the take's word start by the phrase's `stretch`.
- `craft_bar.recorded_lines` follows the chain lean → stretch → take, checks both identities at each step, and
  scales the take's words by the factor, so pace, stress and first-word measures read the slowed line.

The bound of 1.25 keeps a stretch inside what a phase-vocoder stretch carries without audible smearing; a take is
never sped up, since a faster read is a new take's job.

## Rejected

- **A new take at a lower `speed`.** The reviewer ruled it out, and it costs provider characters and changes the read.
- **Transcribing the slowed clip.** It needs the key and a request on every build, and the take's own transcript
  scaled by a known factor is exact for a uniform stretch.
- **ffmpeg `atempo`.** It is also pitch-kept, but rubberband's transient handling keeps consonants cleaner at these
  factors.
