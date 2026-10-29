---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0037: The cover fingerprint is the drawing, not the source of the code that draws it

- Status: accepted; implemented 2026-10-29 (`social.fingerprint`, `social.render_steps`, `social.video_size`,
  `social.migrate_manifest`, `thumbnail.ENGINE_ARGS`, `thumbnail.ENCODER_ARGS`, `delivery.json` 1.1.0,
  `instagram_posts.py migrate`; `tests/test_social.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Amends [ADR 0013](0013-designed-thumbnails-and-publish-gate.md), decision 5
- Back to the [library README](../../README.md)

## Context

The publish gate of ADR 0013 records a post fingerprint for each delivered video. One of its inputs was the SHA-256
of the whole `thumbnail.py` source. Commit f7c86d3 changed only `ThumbnailError`'s base classes (it gained
`SrstudioError`, ADR 0034) and the import that names it. No cover could draw differently, yet every fingerprint
changed, and `instagram_posts.py check` reported every published video as drifted. With `thumbnail.py` restored to
its f7c86d3^ bytes, only the five Saga videos whose scenes really changed drift.

Published videos are frozen. A gate that cries drift on every refactor of the layout module teaches its readers to
ignore it, or to redeliver covers that did not change.

Facts that shaped the design:

- A cover is made from its backdrop frame, the document `thumbnail.compose` lays out, and the fixed steps that turn
  that document into a JPEG: the frame choice, how the frame is written, the scene variant it is drawn in, the
  engine's arguments and the encoder's quality.
- `compose` is pure. For a thumbnail, a font and a size it returns the same bytes every time.
- The backdrop's pixels are already pinned elsewhere in each entry: by the render's SHA-256, by the scene's SHA-256
  for a cover drawn from the scene, and by the thumbnail's time inside its spec.
- Of the 84 rendered videos, 77 are 1080 × 1920 and 7 are 1080 × 1080. `grid_box` and `layout` treat the two shapes
  differently.

## Decision

1. **The fingerprint holds the drawing.** Besides the caption, the thumbnail spec and the headline font, it digests
   the document `compose` returns for the post's own thumbnail at the video's own size, with the sources `render`
   gives it (`thumbnail.BACKDROP_FILE`, `thumbnail.FONT_FILE`), and the render steps. The source of `thumbnail.py`
   is no longer an input. A docstring, a base class or a rename that leaves every composed document byte-identical
   changes no fingerprint. A change to the layout, to the document or to a render step changes it.
2. **The render steps are named constants that `render` uses.** They are `thumbnail.ENGINE_ARGS` (`-f 0`, the one
   frame of the document), `thumbnail.ENCODER_ARGS` (`-q:v 2`), `social.BACKDROP_ARGS` (how `take_frame` writes its
   frame), `social.FRAME_SLACK` (the frame on screen at t is floor(t × fps + 1e-6)) and `social.COVER_VARIANT`.
   `social.render_steps()` digests them all. A step cannot change without changing the fingerprint, because the
   code that runs the step reads the same constant.
3. **The size is the video's, read from its MP4 index.** `social.video_size` reads the width and height from the
   sample entry of the first video track. It runs no ffprobe, and it agrees with ffprobe on all 84 renders.
   `InstagramPost.deliver` refuses a video whose index names another size than the one it decodes at, so the size
   fingerprinted is always the size drawn.
4. **`check` runs no engine, ffmpeg or ffprobe.** It still hashes files and composes documents in memory. A post
   whose cover can no longer be laid out (a headline too wide, for one) is reported as a drift of its own: "the
   cover cannot be drawn now".
5. **`delivery.json` is 1.1.0.** The shape is unchanged. The meaning of `post` changed, so the version did.
   `read_manifest` refuses a 1.0.0 manifest with `ManifestVersionError`, and the message names
   `instagram_posts.py migrate`. `check` reports that as drift. `publish` refuses a manifest of any other version
   instead of replacing it with a full delivery. Covers are not redelivered over a manifest this srstudio cannot
   read correctly.
6. **The migration is one-time and works only on proof.** `instagram_posts.py migrate OUT RENDERS --fonts DIR`
   (`social.migrate_manifest`) handles a 1.0.0 manifest only.
   - It rewrites an entry's `post` only when the stored value equals the 1.0.0 fingerprint of the post now,
     recomputed with one of `social.LEGACY_LAYOUTS`. A match proves the delivery was made from this caption, spec,
     font and scene, and with a layout that draws as today's does.
   - `LEGACY_LAYOUTS` holds the SHA-256 of the two `thumbnail.py` sources that 1.0.0 deliveries hashed:
     - `LEGACY_LAYOUT_7CDAFF4`, the file as 7cdaff4 wrote it (`git show f7c86d3^:src/srstudio/thumbnail.py`);
     - `LEGACY_LAYOUT_F7C86D3`, the file as f7c86d3 left it (`git show f7c86d3:src/srstudio/thumbnail.py`).
   - The two count as one layout. `git diff f7c86d3^ f7c86d3 -- src/srstudio/thumbnail.py` is two insertions and
     one deletion: `from .errors import SrstudioError`, and `SrstudioError` added to the bases of `ThumbnailError`.
     Nothing `compose` or `render` does depends on either line.
   - The set is closed. No later source hash is ever added: after the migration, the drawing fingerprint is the
     only scheme, and a manifest at 1.1.0 is never migrated again.
   - Every other entry is kept as it was, so `check` still reports it. That includes the five changed Saga scenes
     and a video that is no longer published.
   - `render`, `ig` and `cover` are never touched. Nothing is drawn or delivered.
   - It reads and replaces the manifest under `delivery.json.lock`, through a temporary file renamed in one step.
   - `--dry-run` prints the same plan and writes nothing, not even the lock.

## Rejected alternatives

- **Re-pinning the manifest.** This means running `deliver` again, or rewriting every `post` to the new value
  without a check. A new delivery redraws covers that are published and frozen. A blind rewrite blesses entries
  that drifted for real, which would hide the five changed Saga scenes. Neither can tell a false drift from a true
  one. The proof-based migration can.
- **A hand-bumped `LAYOUT_VERSION`.** This is a control that depends on someone remembering it. A forgotten bump
  hides a real layout change. An unneeded bump drifts every published video, which is the defect this decision
  fixes. The composed document is the layout's output, so digesting it needs no one to remember anything.
- **A fixed reference size.** This would be one size for every fingerprint, with no need to read the video. A
  change that only moves the square layout would leave the 7 square videos' fingerprints unchanged. The video's
  own size costs one read of its index.
- **ffprobe in `check`.** The gate would need ffmpeg installed to answer a question about hashes. It would also be
  slower, and `check` must be able to run where no media tools are installed.

## Consequences

- Refactoring `thumbnail.py` no longer drifts the delivery, as long as no composed document changes. The suite
  shows this by pointing the module at an edited copy of its source.
- A change to the scene SDK that changes the bytes of the composed document drifts every cover, even if the JPEG
  would come out the same. The engine reads those bytes, so this is counted as drift.
- Two videos were delivered on 2026-10-29 by code that already had f7c86d3's `thumbnail.py`. Accepting that
  source's hash lets their entries migrate on the same proof, with no redelivery.
- An entry can only be proven against a post the migrating checkout ships. A video delivered from a release that is
  not in that checkout is kept as "no longer published". Run `migrate` from a checkout that ships every delivered
  release.
- The rehearsal ran on copies of the delivery as it stood on 2026-10-29, which held 83 entries.
  - With the releases of this change, `migrate --dry-run` and `migrate` printed the same plan: 76 migrated and 7
    kept. Five of the kept were the Saga videos whose scenes changed. The other two were videos whose releases are
    on another branch, so they were kept as no longer published.
  - With that other branch's releases, it printed 78 migrated and 5 kept, and `check` listed only the five Saga
    videos.
  - Each migrated entry changed only its `post`.
- Covers drawn before and after this change from the same render are byte-identical. This was checked on a
  portrait post, a square post and a post drawn from its scene.
