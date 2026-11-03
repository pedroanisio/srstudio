---
updated-by: OpenAI Codex (GPT-6)
---

# Sign, package and deliver an episode

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Build and validate the scene before packaging it. Timeline and thumbnail positions use the episode clock; output roots, fonts and renderer paths are explicit command inputs. Delivery examples below describe validation failures and preserved output.

Library paths below are relative to the srstudio repository. Commands that read the reels (`srstudio number`,
`srstudio strict`) run from the srstudio-episodes root, where `episodes/` and `generated/` resolve.

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
  [episodes/instagram_posts.py](https://github.com/pedroanisio/srstudio-episodes/blob/develop/episodes/instagram_posts.py) derives its `POSTS` map from the releases; each episode
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
- **Doubled captions.** `deliver` refuses a video being delivered when two caption layers at one height overlap, so
  no frame shows two lines stacked on one band (`craft.doubled_captions`, `releases.doubled_captions`). Videos already
  published are not read: they are frozen. `Episode.spoken_captions(tail=, lead=)` times each caption to its phrase
  and cuts it where the next phrase starts, so lines spoken close together never share the band.
- **Delivering.** The publish gate (`episodes/instagram_posts.py deliver`, `check`, `migrate`), the outbox to Drive
  (`episodes/publish_drive.py`) and the pilots' road (`episodes/publish_pilots.py`) are the reels' commands. They run
  from the srstudio-episodes root and are described in its [delivery guide](https://github.com/pedroanisio/srstudio-episodes/blob/develop/docs/delivery.md).

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
