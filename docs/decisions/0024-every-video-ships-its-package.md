---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0024: Every published video ships its scene video package, and the gate holds back one without it

- Status: accepted and implemented, 2026-10-28 (`srstudio.package`, `outbox.NO_PACKAGE`, `episodes/publish_drive.py`;
  `tests/test_package.py`, `tests/test_outbox.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator asked that every video in the outbox carry its `.vpkg.zip`, and that the gate enforce it. Only the
recreations had one: they arrived as packages in `videos-styles/`. The episodes srstudio builds shipped as a video,
a caption and a cover, so nobody could rebuild, audit or re-render them from what was published.

## Decision

- **The gate requires a package.** `outbox.ready` holds back a current video that has no package, as drift with the
  reason `NO_PACKAGE`, exactly as it holds back a re-rendered one; `publish_drive.py` lists it and exits 1.
- **Received packages win.** A recreation ships the package it came with, found in the `--packages` folders
  (`videos-styles/` by default). srstudio never repacks someone else's package.
- **Original episodes are packed, then proven.** `srstudio.package.pack` copies the project, writes its `vpkg.json`
  (the primary scene, the render step and the engine version it was validated with), and packs it with the
  `scenerender-vpkg` tool from `sr-core`. The package is unpacked (every file checked against its SHA-256) and the
  engine validates the unpacked scene, so every file the scene references is inside. Any failed step is a
  `PackageError` and leaves no package; the video is then held back with the reason printed.
- **Versions follow the scene.** While the scene's SHA-256 matches the latest package, that package is kept. A
  changed scene is packed as the next patch version beside the earlier ones, never over them.
- **Tool output stays in `generated/`.** Packages are written to `generated/vpkg/` (folder 700, files 600).

## Rejected alternatives

- **Write our own packer.** `scenerender-vpkg` already defines the format, its schema, the file roles and the
  verification; a second packer would drift from it.
- **Re-render every package to compare it with the delivered video.** Validation proves the package is complete at a
  fraction of the cost; the delivery gate already ties the delivered video to its render.
- **Write `vpkg.json` into `generated/episodes/<slug>/`.** Rebuilds replace those folders; the manifest is written in
  a private copy and only the finished package is kept.

## Consequences

- A package proves the scene can be rebuilt. It does not prove that the delivered render came from this exact
  scene: a scene rebuilt after its render was delivered is packed as it is now.
- Packing needs `scenerender-vpkg` beside the running Python or on the `PATH`, and the engine; without them every
  original episode is held back with that reason.
