---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0032: One release file per episode, episodes run by slug, and lists discovered instead of written

- Status: accepted; implemented 2026-10-29 (`srstudio.releases`, `srstudio.recording`, `srstudio build <slug>`,
  `srstudio record <slug>`, `srstudio catalog --usage`, `episodes/posts/`; `tests/test_releases.py`,
  `tests/test_recording.py`, `tests/test_cli_episodes.py`, `tests/test_sketch_recorders.py`, `tests/test_usage.py`,
  `tests/test_catalog_page.py`, `tests/test_canvas_and_registry.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md); supersedes the last consequence of
  [ADR 0017](0017-measured-part-usage.md) (the hand-written `episodes=` declarations stay as documentation)

## Context

Publishing an episode meant editing four shared places by hand: the `POSTS`, `VIDEOS` and `COVER_SCENES` tables in
`episodes/instagram_posts.py` (1763 lines, edited by every session that shipped a video), the `episodes=` tuple of
every part the episode drew, and the hand lists of episode names in the Collage, Saga and Gloss tests. Each audio
script also carried its own copy of the same `argparse` front end. The tables drifted: a cover scene listed in
`COVER_SCENES` had to match the scene's `cover` variant, and nothing checked that it did.

## Decision

- **A release per episode.** `episodes/posts/<slug with underscores>.py` defines `RELEASE = Release(slug, post,
  video=, scene=, cover=, builder=)`. `releases.load` imports the package and refuses a module without a release,
  a file named for another slug and two releases claiming one video. `releases.items` reads the built scene and
  refuses a release whose `cover` disagrees with the scene's `cover` variant. `episodes/instagram_posts.py` keeps
  its command line and its `POSTS`, `VIDEOS` and `COVER_SCENES` names, now derived from the releases.
- **Episodes run by slug.** `srstudio build <slug> PROJECT` and `srstudio record <slug> PROJECT` find the scripts
  through the releases (`builder=` names a script that is not the slug). `srstudio.recording.main` is the one
  command-line front end of a recorder; `_toon_sketch.recorder` and `_collage_sketch.recorder` build a recorder's
  `main` from the sketch's data.
- **Lists are discovered.** The Collage, Saga and Gloss tests find their episodes from the files on disk. The
  registry no longer takes `episodes=`: which episodes use a part is the measured report of ADR 0017, which
  `srstudio catalog --usage` and `srstudio page --usage` read, and `srstudio usage` resolves each project's builder
  through the releases.

## Rejected alternatives

- **Keeping the tables and adding a consistency test.** The test would catch drift, but every new episode would
  still edit the same shared file as every other session.
- **Releases as JSON or TOML.** A post holds a `Thumbnail` and shares hashtags with its series; Python keeps those
  typed and shared without a second schema.
- **Keeping `episodes=` as documentation.** A declaration nothing checks drifts, as ADR 0017 measured; the usage
  report answers the same question from the builds.

## Consequences

- A new episode adds one release file; it edits no shared table.
- Every delivered post, video name and cover is unchanged: the derived tables equal the previous ones, and every
  episode rebuilds byte-identical.
- The catalog lists a part's episodes only with a usage report; without one it claims none.
