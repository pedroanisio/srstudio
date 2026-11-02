---
updated-by: OpenAI Codex (GPT-6)
---

# Sign, package and deliver an episode

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Build and validate the scene before packaging it. Timeline and thumbnail positions use the episode clock; output roots, fonts and renderer paths are explicit command inputs. Delivery examples below describe validation failures and preserved output.

Run commands from the srstudio repository root.

## Signature

Every episode built with this library carries two recurring marks that sign the work. They are a convention
decided on 2026-10-28 ([docs/decisions/0001-signature.md](../docs/decisions/0001-signature.md)) and implemented in
[src/srstudio/signature.py](../src/srstudio/signature.py). Episode 06 (`five-years`) is the first signed episode; the
seven shipped packages predate the convention and build with `signature=False`.

| Mark | What it is | Where it appears |
|---|---|---|
| **Code** `SR-1028` | A short diegetic code, in the style of Pixar's A113, drawn as stroked glyph paths (no font asset, so it never trips the legibility check) in the location's own colour | Office: on the top sheet of the desk papers. Café: the last line of the menu board. Park: the corner of the park sign. Doodle: the model plate under the printer's output tray |
| **Prop** `signature-cactus` | A small potted cactus, redrawn in the language of each palette (gradients in `OFFICE`/`CAFE`, pen stroke in `MONO`), about 6 % of the frame height | Office: the far corner of the desk. Café: the shelf. Park: beside the bench. Doodle: on the desk, between the laptop and the edge of the frame |

Rules:

- Both marks are drawn by the location builders through `srstudio.signature.code(cv, parent, x, y, height, color=…)`
  and `srstudio.signature.cactus(cv, parent, x, y, scale)`, never by episode scripts, so a new location adds one call
  per mark and an episode cannot forget them. Both return `None` and draw nothing on an unsigned canvas.
- `EpisodeSpec.signature` controls both and defaults to `True`. The seven shipped episode scripts pass
  `signature=False`, because their packages predate the convention and the fidelity tests reproduce them element for
  element; re-signing them is a new package version, not a rebuild.
- The code is `EpisodeSpec.signature_code` (default `SR-1028`); changing it is a project-wide decision, not a
  per-episode one. A character without a glyph (`A–Z`, `0–9`, `-`, `.`, space) raises `ValueError` at build time.
  The groups are ided `sig-code`, `sig-cactus` (then `-2`, `-3`… per location) so `tests/test_signature.py` asserts
  both are present in every location of a signed scene, absent when `signature=False`, and that the `MONO` variant
  adds no gradient paints.
- The marks never carry story information unless an episode opts in (next rule), never sit inside a caption's box or
  on a face, and stay inside the engine's safe area. They must not trigger the legibility check: the code is at
  least the `minTextSize` of the episode's `<accessibility>` or is drawn as paths.
- The cactus may perform ([ADR 0039](../docs/decisions/0039-the-signature-cactus-may-perform.md)). A
  `signature.Act(end, turn=, bloom=, code=)` turns its flower, pops it into bloom on a beat and writes the code
  inline on its pot (`signature.cactus(..., act=)`). `office_wide`, `office_desk`, `office_reverse`, `cafe` and
  `park` take a `cactus=` slot that replaces their own cactus at the same depth, through
  `signature.home_cactus`: on a signed canvas the slot must draw exactly one cactus, so a shot never loses or
  doubles the mark. Without `act=` or `cactus=` every drawing keeps its bytes, which `tests/test_signature.py` pins.

## Instagram captions

Every episode ships with an `ig.txt`: title, description, credit and hashtags, in that order, separated by blank
lines. The caption is data before it is text: `srstudio.social.InstagramPost` holds the four parts and refuses to
write when a limit is broken (title longer than the 125 characters the feed shows before folding, a malformed or
duplicate hashtag, a caption over 2200 characters, an empty title or description). The error is `InstagramPostError`,
with every problem listed.

The account is Okayville, handle @okayville.tv, and the brand is everyday life, animated, not office cartoons. A new
caption carries at most 5 hashtags (`social.HASHTAG_LIMIT`), Instagram's cap since 18 December 2025. The whole caption
counts, so a tag in the description is one of the five. The first delivery holds this
([ADR 0065](../docs/decisions/0065-okayville-and-five-hashtags.md)): `deliver` and `publish_pilots.py` refuse by slug
with `HashtagError` before anything is written. A published post keeps the 6 to 8 it went out with, so writing one
still passes up to `social.PUBLISHED_HASHTAG_LIMIT`, and `check` does not ask.

- Each shipped episode has a release, `episodes/posts/<slug with underscores>.py`, defining
  `RELEASE = srstudio.releases.Release(slug, post, video=, scene=, cover=, builder=)`
  ([ADR 0032](../docs/decisions/0032-releases-recorders-and-discovery.md)). `cover=True` says the cover is drawn from
  the scene's `cover` variant, and the gate refuses a release that disagrees with the built scene. A new release
  also sets `tags=srstudio.releases.Tags(territory, cause, emotion, recurring=, test=, arm=)`, from closed sets the
  account's analytics count ([ADR 0033](../docs/decisions/0033-episode-tags-for-analytics.md)); releases published
  before tags existed leave it `None`. A reel in a second A/B test adds `also=(("sp-speakers", "a"),)`, and a reel on
  the send test adds `send_to=` and `send_line=`
  ([ADR 0080](../docs/decisions/0080-a-brief-in-episode-json-and-giving-a-claim-back.md)).
  [episodes/instagram_posts.py](../episodes/instagram_posts.py) derives its `POSTS` map from the releases; each episode
  script calls `ep.instagram(POSTS[slug])` before `ep.finish()`, so a build leaves `ig.txt` next to the scene.
  Recreations credit the original author in the caption itself.
- Every post designs its **cover**: `InstagramPost(thumbnail=Thumbnail(headline, at, kicker, focus, zoom, place))`
  from [srstudio.thumbnail](../src/srstudio/thumbnail.py) (ADR 0013). The backdrop is the frame of the rendered video on
  screen at `at` (frame floor(t × fps), selected by index, not by seeking), magnified `zoom` times on `focus`; over it
  the engine draws a kicker pill and a one-to-three-line headline in Anton, white with an ink outline, its last line
  in the accent, on an ink band that is opaque outside the grid area. Everything that carries meaning stays inside
  the profile grid's centred 3:4 window (`grid_box`): the headline takes the largest size from 200 px down to
  110 px whose widest line fits and whose block takes at most 38 % of that window, and is refused
  (`ThumbnailError`) when none does. `srstudio.social.take_frame` refuses (`CoverError`) a time after the last
  frame and a blank frame (a fade or a black cut). `post.deliver(folder, video, font=, engine=)` writes `cover.jpg`
  and then `ig.txt`; a post without a thumbnail is an `InstagramPostError`, and on any failure nothing is written.
- **Publish gate.** `python3 episodes/instagram_posts.py deliver <out> <renders> --fonts <dir>` delivers every video
  that drifted (one `<out>/<video name>/` folder with `ig.txt` and `cover.jpg` per `<renders>/<video name>.mp4`) and
  records `<out>/delivery.json` (version 1.1.0): per video, the SHA-256 of its render, of its post fingerprint and
  of the two files written. The post fingerprint is the cover's drawing, not the source of the code that draws it
  ([ADR 0037](../docs/decisions/0037-the-cover-fingerprint-is-the-drawing.md)): the caption, the thumbnail spec, the
  headline font, the document `compose` lays out at the video's own size (read from the MP4 index) and the named
  render steps (`thumbnail.ENGINE_ARGS`, `thumbnail.ENCODER_ARGS`, `social.BACKDROP_ARGS`, `social.FRAME_SLACK`,
  `social.COVER_VARIANT`), so a refactor of `thumbnail.py` that draws the same covers drifts nothing. `check` writes
  nothing, runs no engine, ffmpeg or ffprobe, lists every drift and exits 1: a video re-rendered after its cover was
  made, a changed post, thumbnail or drawing, a cover that can no longer be laid out, an `ig.txt` or `cover.jpg`
  edited or missing, a post without a render, a video delivered but no longer published. A 1.0.0 manifest is
  refused by name; `instagram_posts.py migrate <out> <renders> --fonts <dir> [--dry-run]` moves it to 1.1.0 once,
  rewriting only the entries that provably hold the 1.0.0 fingerprint of the post they have now, under the
  delivery lock; it draws and delivers nothing.
  Every render must exist before `deliver` writes anything; current videos are left untouched. `--only <video name>`
  (repeatable) delivers the named videos alone, needing only their renders, while another post waits for its render;
  the other manifest entries are kept as they were, so `check` still reports their drift. A release declared
  `frozen=<fingerprint>` ([ADR 0040](../docs/decisions/0040-frozen-releases-at-an-accepted-drawing.md)) is a published
  video whose post now draws another cover: the gate takes it as current at that one drawing (every other check
  still holds), `deliver` leaves it as published, and `check` lists it. Only the operator freezes a release.
  The font is installed
  into `--fonts` and pinned there (`generated/fonts`); the deliveries live in `generated/renders/ig/`. With
  `SRSTUDIO_RENDERS` and `SRSTUDIO_FONTS` set, the test suite runs `check` against the real delivery, so a
  re-render without a new delivery fails the quality gate.
- **Doubled captions.** `deliver` refuses a video being delivered when two caption layers at one height overlap, so
  no frame shows two lines stacked on one band (`craft.doubled_captions`, `releases.doubled_captions`). Videos already
  published are not read: they are frozen. `Episode.spoken_captions(tail=, lead=)` times each caption to its phrase
  and cuts it where the next phrase starts, so lines spoken close together never share the band.
- **Outbox and packages** ([ADR 0024](../docs/decisions/0024-every-video-ships-its-package.md)).
  `python3 episodes/publish_drive.py` stages every video that passes the gate in `generated/outbox/<video name>/`
  (video, `ig.txt`, `cover.jpg` and its `.vpkg.zip`) and copies it to Drive (`--stage-only`, `--dry-run`). A video
  without a package is held back like a drifted one. A video whose release is in an A/B test
  (`releases.Tags(test=, arm=)`) is staged with an `ab.json` (`{"test": ..., "arm": ...}`) that the posting job
  reads, hashed in `outbox.json` like every staged file. A second test goes beside them as `"also": [{"test": ...,
  "arm": ...}]`, from `Tags(also=)`. The recipient test rides in the same file: `recipient=` is
  its arm, and arm `b` adds `to=`, who the viewer sends it to, from `releases.RECIPIENTS`. A recreation ships the package it was received with
  (`videos-styles/`); an original episode is packed by `srstudio.package` from `generated/episodes/<slug>/` into
  `generated/vpkg/` with `scenerender-vpkg`, unpacked and checked against its SHA-256s, and its scene validated by
  the engine. Each call builds and verifies a candidate, comparing its resolved files and metadata with the latest
  release. Changed assets, supporting files or metadata produce the next patch version; unchanged content keeps
  the existing archive. The tests cover each limit's failure path, the episode hook, every shipped post (each
  with a thumbnail and one video), the frame selection on a synthetic video whose frames differ (first, middle and
  last frame), frames outside the video, blank frames, unreadable probes, deliveries that leave no files when the
  backdrop or the engine fails, and the gate: a fresh delivery, never delivered, a re-render (and that only it is
  redelivered), a changed post, edited and missing files, a dropped video, every untrustworthy manifest and a
  missing render. `tests/test_thumbnail.py` covers every refused spec, the grid window, the layout inside it at
  both places and both frame shapes, the size and height refusals, the composed scene, and the engine render with
  its failure path.
- **Pilots** ([ADR 0054](../docs/decisions/0054-pilots-have-their-own-road-to-drive.md)). A pilot for a future channel is
  not published and must never reach Okayville, so it has its own road: `python3 episodes/publish_pilots.py FOLDER`
  (`--series`, `--stage-only`, `--dry-run`). `FOLDER` holds one folder per slug with `<slug>.mp4`, `cover.jpg`, `ig.txt`,
  `sources.md`, `notes.md` and a package, `vpkg.zip` or `<slug>-<version>.vpkg.zip`, delivered as `vpkg.zip`. It stages
  `generated/pilots/<series>/` (folders 700, files 600; `mind` by default, or `maps` or `news`) with `manifest.json`
  beside the folders, shaped like `outbox.json`, and uploads to `gdrive:srstudio/pilots/<series>` with `outbox.push`:
  `rclone copy`, then `rclone check`, never a delete.
  It refuses a missing or empty file, blank `sources.md` or `notes.md`, a slug that is not one plain name, a slug
  Okayville has used (release slugs, video names, folders in `generated/renders/ig`), any staging folder but
  `generated/pilots/<series>`, any remote outside `gdrive:srstudio/pilots/<series>`, and a new News pilot short of the
  comedy floor ([ADR 0064](../docs/decisions/0064-comedy-floor.md)): `comedy-author` and `comedy-reviewer` in the frontmatter of
  its `notes.md`, the lower at 14 or above. The remote is judged after normalising, and rclone is given the normal form,
  so `pilots/../ready-to-publish` is refused. No systemd unit watches the staging folder and none runs this tool.
  `FOLDER` is the whole set: staging replaces the last stage.

### The Okayville show signature

A reel in the show's look carries one cover and one corner bug ([ADR 0074](decisions/0074-okayville-show-signature.md)).
The cover is a `srstudio.thumbnail.ShowCover`: a solid band with OKAYVILLE, `#N` and the premise in at most 5 words,
over the reel's own art. The bug is the part `show-bug`, which `srstudio build` draws above the camera for a release on
that cover and for no other. Numbers come from `srstudio number`: `base` sets the publishing side's count once, `claim`
takes the next one before the final build, `list` prints the ledger at `generated/okayville/numbers.json`. A series has
its own count with `--series`, and `outbox` writes `episode.json` beside the video, exactly `{"number": N, "series":
"saga" or "", "series_number": n}`, with 0 outside a series (`show_numbers.EpisodeDocument`). `srstudio.show_gate`
refuses a first delivery out of the look. `srstudio number claim <slug> --brief send-v1` records the brief a reel was
made to, and `episode.json` then carries `"brief"` too; a reel without one keeps the three fields. `srstudio number
release <slug>` gives back a claim on a reel never delivered ([ADR 0080](decisions/0080-a-brief-in-episode-json-and-giving-a-claim-back.md)).

### Strict findings at first delivery

`srstudio.strict_gate` reads a new reel's `qa/render-report.json` at first delivery
([ADR 0078](decisions/0078-strict-findings-at-first-delivery.md)). A `--strict` finding refuses the reel unless
`episodes/strict/<slug>.json` proves it false on the master's own frames, signed off by a reviewer who is not the
author. `srstudio strict` lists the reels shipped that way, with their numbers and frames, and how many of the delivered
reels that is.
