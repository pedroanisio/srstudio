---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0226: An enhancement counts in either repository

- Status: accepted (2026-11-03, fixes the mechanics of the operator's auto-enhance rule after the split; the rule
  and its mode are unchanged)
- Back to the [library README](../../README.md)
- Builds on [ADR 0056](0056-auto-enhance.md) and [ADR 0220](0220-episodes-repository.md)

## Context

The auto-enhance gate (ADR 0056) read the git history of one repository with the monorepo's paths: library changes
under `src/srstudio/` or `tools/`, the skill at `.claude/skills/funny-reels/SKILL.md`, a reel's own files under
`episodes/` and `pilots/`. After the split (ADR 0220) `deliver` and `publish_pilots.py` pass it the srstudio-episodes
checkout, so:

- a library change with `Enhances: <slug>`, which now lands in srstudio, never cleared a delivery; only a skill bump
  or an episodes `tools/` change could;
- `srstudio enhance` read `episodes/auto_enhance.json` beside its `--scripts` folder and printed `on` when that file
  was absent, as if it had read it;
- `srstudio enhance on|off` run in srstudio created `episodes/auto_enhance.json` inside the library, where nothing
  reads it.

## Decision

1. **Two histories.** A claim is read from `develop` of srstudio-episodes and from srstudio at the commit the
   episodes' `pyproject.toml` pins. The pin is the library the next reel builds on, so a library enhancement counts
   once the episodes pin a commit that holds it, as an episodes one counts once it is on `develop`.
2. **Paths per repository.** Each history carries a `Layout`. In srstudio-episodes the process is `tools/` (with the
   reel and pilot processes) and the skill; in srstudio it is `src/srstudio/` and `tools/`. srstudio's layout also
   keeps the skill and the reel folders, because its history up to the split is the monorepo's, so claims made
   before the split read as they did. A `src/srstudio/` inside srstudio-episodes is not the library and does not
   count.
3. **The callers name both checkouts.** `refused(videos, repo, sdk)` takes the episodes repository and the srstudio
   checkout. The delivery commands pass `$SRSTUDIO_SDK`, else the checkout the imported `srstudio` package came
   from; `srstudio enhance` takes `--sdk`, then the same two. A folder that is not a git checkout of srstudio, a
   `pyproject.toml` that pins no single srstudio commit, or a library that lacks the pin is an `EnhanceError`: the
   gate fails closed. With the mode off, or no video new, neither the pin nor the library is read, so off still
   just delivers.
4. **The newest claim speaks across both.** Each row carries its commit time and its repository; with only bad
   claims, the newest one's problems are the refusal.
5. **The command says where the mode came from.** `srstudio enhance` prints `on (read from <file>)` or
   `on (the default: <file> does not exist)`. `status`, `check`, `on` and `off` refuse with exit 2 outside an
   episodes repository (one whose `pyproject.toml` pins srstudio), so nothing is written in the library. `check`
   lists the unsound claims on the branch checked out in each repository, so an srstudio branch can be checked
   from an episodes checkout with `--sdk`.

## Alternatives rejected

- **Read the srstudio history at its `develop`.** A library change on `develop` that the episodes do not pin yet
  is not in the next reel's build.
- **Fall back to `../srstudio` beside the episodes.** It names a layout of one workstation, and a stale sibling
  would answer for a library it is not.
- **Parse `pyproject.toml` as TOML.** `tomllib` is Python 3.11 and srstudio supports 3.10; the pin is read from its
  quoted dependency string, as the episodes' `tools/gate.sh` reads it, and anything but exactly one match is refused.

## Consequences

- The ledger of `srstudio enhance` lists both repositories, each row prefixed with `srstudio-episodes` or `srstudio`.
- A library enhancement clears its video only after the episodes move the pin past it.
- The delivery commands need an srstudio git checkout while the mode is on; a non-editable install must set
  `SRSTUDIO_SDK`.
