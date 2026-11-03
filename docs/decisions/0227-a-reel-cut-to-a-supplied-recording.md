---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0227: A reel cut to a supplied recording

- Status: accepted (2026-11-03, for the Okayville trend reel `my-phone-searches`)
- Back to the [library README](../../README.md)
- Builds on [ADR 0056](0056-auto-enhance.md) and the voiced Toon sketch (`srstudio.sketch`, `srstudio.toon_sketch`)

## Context

A trend reel is built on a sound someone else made: one mixed file with speech, a bed and room tone in it, and a
credit the post must carry. The voiced Toon sketch only knew takes we record per line, one ElevenLabs request each,
so a reel on a supplied sound had no way to get its beats, captions and mouths onto that file's words.

## Decision

1. **`srstudio.supplied`** decodes the file, checked against the SHA-256 the episode pins, bit-exact to
   `audio/supplied.wav`, so the same file gives the same bytes and the same cached reading.
2. **One reading, verified.** The words come from one speech-to-text reading (`ElevenLabsClient.transcribe`, cached by
   the file's digest). It is model output, so `locate` parses it against the sketch's lines: contiguous runs of heard
   words in line order, each heard as its line (`check_transcript`, with the line's `heard=`), every word inside the
   file and in time order, no audio events and no words left over. Anything else is a typed `SuppliedError` and
   nothing is written. The default hearing reads the cache with no key; only a missing reading asks for the cloud
   consent and the key.
3. **One track, the whole file.** `narration.json` holds a single item from second 0 for the file's length. The file
   is already mixed, so it is never cut per line; a line said together, by phone or at a gain is refused.
4. **Letters spread evenly over heard words.** A reading gives words, not letters, so each word's letters share its
   span evenly and a space spans the gap; `voiced/speech.json`, `beats.json` and `mouths.json` are written as a
   recording would write them, and a voice with no character on screen gets its viseme track from `mouth_track` for a
   dress that draws its own mouth.
5. **The credit travels with the manifest** (`voice.<speaker>.credit`, `tts_engine: "supplied"`); the post's caption
   carries it for the reader.
6. **`recorder(...)`** gives a reel's `_audio.py` its `main`: `PROJECT --supplied FILE [--ffmpeg PATH]`.

## Alternatives rejected

- **Slice the file per line into takes.** The file holds sound between the lines; slicing drops it or doubles it.
- **Hand-written word times.** Unverifiable, and wrong on the next file; the reading is checked instead.
- **A forced aligner for letter times.** A new dependency for a precision the drawn mouths do not show.

## Consequences

- A reel built this way carries audio that is not ours; whether it may post with that audio is a release decision,
  not the library's.
- The file and every render of it stay out of git; only its SHA-256 and the reading's cache key are in the episode.
