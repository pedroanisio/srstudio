---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0220: Episodes live in their own repository

- Status: accepted (2026-11-03, the operator: "faca a sepraracao agora")
- Back to the [library README](../../README.md)

## Context

One git repository held both the library and everything built with it:

| Folder | Content | Files |
|---|---|---|
| `src/srstudio/` | the library and its CLI | 426 |
| `episodes/` | one builder, recording script and data module per reel, the releases and the delivery commands | 534 |
| `pilots/` | the shows' captions, sources and posts | 148 |
| `bible/` | the cast bible | 4 |
| `tests/` | 772 test modules, 137 of them reading `episodes/`, `pilots/` or `bible/` | 745+ |

The dependency ran one way: no module under `src/srstudio` imports an episode. But every reel batch carried library
parts with it, so library and reels shared one history, one merge queue and one gate of about 29,000 tests that takes
about two hours. On 2026-11-03 a batch's library branch landed seven parts that broke the ADR 0147 hand table, which
the batch's focused tests never ran.

## Decision

1. **The library stays here.** `srstudio` holds `src/`, its tests, examples, tools and documentation, including every
   decision record.
2. **The production moves to [srstudio-episodes](https://github.com/pedroanisio/srstudio-episodes).** That repository
   holds:
   - `episodes/`, `pilots/` and `bible/`;
   - the delivery commands under `episodes/`;
   - the reel and pilot processes and the lane check (`tools/govern/`);
   - the systemd units (`tools/systemd/`);
   - the two studies that import reel modules (`examples/clay_sofa`, `examples/paintover_proof`);
   - the funny-reels skill;
   - every test that reads those folders.

   Its layout keeps the same folder names at its root, so commands run from there keep their relative paths.
3. **The episodes pin the library.** srstudio-episodes declares one srstudio commit as its dependency. Its gate
   builds the library at that commit and tests the reels against it. Moving the pin is a commit in srstudio-episodes.
4. **Commands read the production folders from where they run.** `srstudio bible` defaults to `bible`,
   `episodes/posts` and `episodes` under the current folder, like `srstudio build` and `cover_proof` already did.
   `bible_rig.REPO` and `bible_cli.REPO`, which named this checkout, are gone.
5. **Tests that span both trees are split by tree.** Each repository checks its own sources for:
   - engine calls outside the GPU lock;
   - roads to rclone;
   - the retired handle;
   - URL-only DejaVu notes;
   - cited decision records.

   srstudio-episodes checks its records against this repository's `docs/decisions`. The skill's own tests and the
   pregate's publishing rule leave with the reels. The quick gate here no longer runs `enhance check`, because that
   check reads the reels.
6. **History stays here.** srstudio-episodes starts from a snapshot of this repository at the split commit and names
   that commit. `git log` here still shows every reel's history up to the split.

## Rejected alternatives

- **Keep one repository.** It keeps the shared gate and merge queue that made reel batches carry library changes
  past their tests.
- **A git submodule of the library inside srstudio-episodes.** It pins just as well, but every checkout and worktree
  would then clone the library a second time, and the shared virtual environment would import the other copy.
- **Rewrite the history of the moved paths into the new repository.** git-filter-repo is not installed on the
  workstation, and on 2026-11-03 the machine had failing hardware. The history is kept, here, instead.

## Consequences

- A reel build needs the library installed at the pin. The workstation's shared environment installs this checkout,
  so a reel built there uses whatever this checkout holds. The gate in srstudio-episodes uses the pin.
- The library's coverage is measured without the reels' tests.
- Paths change for the running services: the Drive publisher, the catalog's `--releases`, `govern` processes and the
  skill's link now point into srstudio-episodes.
