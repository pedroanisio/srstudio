---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0054: Pilots have their own road to Drive

- Status: proposed (2026-10-30); the operator authorized a separate delivery path for the Mind pilots, and this records
  how it was built
- Author: Claude Opus 5.5 in Claude Code
- Builds on [ADR 0024](0024-every-video-ships-its-package.md)
- Back to the [library README](../../README.md)

## Context

Anything in `gdrive:srstudio/ready-to-publish` can be posted to @tuxmeme, and a write to `generated/renders/ig` pushes
to that folder through the `srstudio-drive` unit. Pilots for a future channel are not published. They must not be able
to reach @tuxmeme through a mistyped flag, a shared slug or a path trick.

## Decision

`episodes/publish_pilots.py` is a separate command that reuses `outbox.stage` and `outbox.push`. It allows, rather than
denies: the remote must normalise to `gdrive:srstudio/pilots/<something>`, and rclone receives that normal form; the
staging folder must be `generated/pilots/mind`. A slug @tuxmeme has used is refused. `Bundle.names` and
`stage(manifest=)` were added so a package can be delivered as `vpkg.zip` and the manifest named `manifest.json`.

## Rejected alternatives

- **A `--pilots` mode on `publish_drive.py`.** One flag away from the wrong folder, and that command's defaults are the
  ones that post. It also runs the publish gate, which reads releases, and a pilot has none.
- **Delivering through `generated/renders/ig` under a separate name.** Any write there fires the `srstudio-drive` unit.
- **A deny list naming `ready-to-publish`.** It would allow every other folder, and every other rclone remote, by
  default. The name is still refused anywhere in the path, in any case, for the message and as a second line.
- **Copying the stage and push code.** A second copy of the hashing and the verify step would drift from the first.

## Consequences

The remote name `gdrive` is fixed, so a new remote needs a code change. The pin to `generated/pilots/mind` means a
second channel needs one too, and that change is a deliberate one. The released list comes from this checkout's
releases and the local delivery folder, so a slug released only on an unmerged branch is not seen.
