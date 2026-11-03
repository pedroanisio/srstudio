---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0170: Approved files are write-once

- Status: proposed (2026-11-01), on the operator's approval to port four ideas from pnkit; written by Claude Opus 5.5
  in Claude Code
- Source of the idea: pnkit, the operator's other kit, `pnkit/files.py` at commit 7d935e5 (`write_once`, `next_free`,
  `write_next`), rewritten here in srstudio's style rather than copied
- Back to the [library README](../../README.md)

## Context

A master script ran again, its `--strict` check failed, and the good master it had made before was overwritten:
`scene-render encode` writes the master even when it exits on a finding, and nothing stood between the engine and the
master's path. The same shape exists wherever a re-run writes a file whose bytes were approved, paid for or shipped.
pnkit met it when an approved score excerpt was replaced by a re-run of the tool that made it, and answered with
write-once helpers.

## Decision

1. **`srstudio.files`** holds the rule. `write_once` writes bytes where nothing is and raises `WriteOnceError`
   (an `SrstudioError` and a `FileExistsError`, code `files.exists`) otherwise. `install_once` moves a finished file
   to a free path. `next_free` gives `excerpt-v2.wav`, `excerpt-v3.wav`..., and `write_next` and `install_next` claim
   it. `write_same` lets bytes derived from an approved file (a WAV decoded from its take) pass when they are already
   there, identical. `must_be_free` is the check a costly run makes before it starts.
2. **The check and the create are one operation.** pnkit opens with mode `"x"`. Here the bytes go to a private stage
   beside the target, are flushed, and take the target's name with `link(2)`, which fails when anything has the name,
   a symbolic link included, dangling or not. Two processes cannot both win a path, and no reader sees a half-written
   file under its final name. Where a file system has no hard links, `O_CREAT | O_EXCL` claims the name instead.
   The search for a free name stops after `files.MOST` tries.
3. **Masters.** `srstudio master <scene> -- --strict ...` (`srstudio.master.encode`) refuses before the engine starts
   when the master's place is taken, so a re-run spends nothing and replaces nothing. `--next` writes the new master
   beside the old one; promoting it is an act of its own. The engine encodes into a private stage with `--out-dir`, so
   every setting of the document's output holds, and each file it wrote is installed write-once at the same place.
   A `--strict` finding still installs the master, as the engine always did, because a record proving the finding
   false is measured on that master (ADR 0078), and the command exits with the engine's status.
4. **The call sites changed.**
   - `master.encode`, the new path for every reel master (`generated/renders/<slug>.mp4`);
   - `episodes/pilots/pedro_drive.py` `encode`, the pilot master beside its scene;
   - `voice.ElevenLabsClient.synthesize`, `.sound_effect` and `.transcribe`: each take's MP3 and timing record, each
     effect's MP3 and record, each speech-to-text record, and their WAVs through `write_same`;
   - `compose.MusicClient.compose`: each song's MP3 and record, its WAV through `write_same`;
   - `package.pack`: each `<slug>-<version>.vpkg.zip`.
   A cache entry with some of its files and not others is refused before the paid request (`voice.refuse_half_written`):
   before, such an entry was paid for again and written over; now it is named and kept.
5. **The sites that stay overwritable**, each a measurement or a view derived from approved bytes and held by a hash:
   - the render report (`qa/render-report.json`): a measurement of the last encode, re-run each time;
   - `voice-transcript.json` and `timeline.json` from `takes.record`, `song` and `interview`: derived from the takes,
     written again on each recording run;
   - `ig.txt` and `cover.jpg` from `InstagramPost.deliver`: drawn from the render and the post, both upstream, and
     hashed into `delivery.json`, so `check` names any change; the gate's redelivery of a drifted reel rewrites them;
   - `outbox.stage`: a mirror built beside the old one and swapped in whole, hashed in `outbox.json`;
   - ledgers and records updated in place under a lock or by design (`show_numbers`, `bible_lock`, `parts` build
     records, `figure_record`, `auto_enhance`), and the font pin (`fonts.install`), whose lock holds the digest.
6. **Strict records** (`episodes/strict/<slug>.json`) are written by people, not by the library (ADR 0078), so no
   library call site exists to change.

## Consequences

- A re-run of `srstudio master` over a good master stops with exit 2 and the master's path, before any render.
- `--next` leaves the report beside the document describing the new encode, not the master at the old path. The
  delivery gate reads that report for the master at `<slug>.mp4`, so whoever promotes a `-v2` master moves it into
  place and runs the gate again; a report never describes a master it did not measure once the promotion is done.
- A half-written voice cache entry is now an error to clear by hand rather than a silent new paid request.

## Alternatives rejected

- **Copy pnkit's `open(path, "xb")`.** It refuses the same names, but a crash mid-write leaves a truncated file under
  the final name, which the next run then refuses to replace. The stage and the link make the name appear only with
  every byte behind it.
- **Make every master path write-once inside the engine.** The engine is not this repository's, and filing engine
  changes is the operator's.
- **Back up the old master and overwrite.** It keeps the bytes but moves them off the path delivery reads, so a failed
  re-run still becomes the reel; the point is that the good master stays where it is.
- **Make the delivered cover and caption write-once too.** They are a view of the render and the post, hashed by the
  gate, and the gate's repair for a drifted reel is to draw them again; freezing a published reel is the operator's
  `frozen=` (ADR 0040), not a file mode.
