---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0224: The engine comes out of its published image and runs on the host

- Status: accepted (2026-11-03, the operator asked to replace the local engine with its Docker image and to make
  srstudio work on scene-render 0.9.0)
- Back to the [library README](../../README.md)
- Builds on [ADR 0171](0171-one-gpu-job-at-a-time.md)

## Context

srstudio runs the engine at `generated/bin/scene-render`, a link to a binary unpacked by hand from a GitHub release
(0.8.0). scene-render 0.9.0 has a tag but no GitHub release: it is published only as the image
`pedroanisio/scene-render:0.9.0` on Docker Hub, built from the tag by the repository's `Dockerfile`, which records the
commit in `/usr/share/doc/scene-render/COMMIT`.

Measured on 2026-11-03 on this machine (RTX 3050, NVIDIA Container Toolkit 1.20.1), ten calls each:

| One engine call | Seconds per call |
| --- | --- |
| The binary on the host | 0.35 |
| `docker exec` into a running container | 0.40–0.44 |
| `docker run` per call (scene-render's `tools/docker/scene-render`, commit aaaa9bb) | 0.70–0.75 |

Every render and encode holds the GPU lock (ADR 0171), so a container's start-up is paid in turn: the 121 test files
that run the engine took 1,650 s through `docker run` against 1,048 s on the host binary.

Running in the container also needs work the host binary does not: the engine starts `resolve` providers such as
`srstudio-elevenlabs` (this interpreter), which do not exist in the image, so scene-render relays them to the host;
the container sees only the folders mounted into it, so a document reading `../fonts` or another episode's audio
fails `A01` unless `SCENE_RENDER_MOUNTS` names the workspace; and a SIGKILL on the `docker` client leaves the
container rendering after the GPU lock is released.

## Decision

- `tools/engine_install.py VERSION` pulls `pedroanisio/scene-render:VERSION`, copies the engine and its commit out of
  a stopped container, and installs them at `generated/bin/scene-render-vVERSION` only when the binary reports
  VERSION, its commit is the commit of the tag `vVERSION` in the image's source repository, and it renders a smoke
  scene on this machine. `engine.json` beside it records the version, image, digest, commit and source.
- An installed version is never replaced by another image. `--activate` points `generated/bin/scene-render` at it
  in one rename; the previous version stays for a switch back (`ln -sfn` to its folder).
- The engine runs on the host. Docker is how a version arrives, not how it runs.

## Alternatives rejected

- **`docker run` per call** (`tools/docker/scene-render`): twice the per-call cost, mounts that must name the
  workspace, a provider relay, and an orphaned container on SIGKILL.
- **One long-lived container and `docker exec`**: close to the host's cost, but it must be started, restarted on a
  new version and mounted once for every path, and it keeps the provider relay and the SIGKILL orphan.
- **Waiting for GitHub releases**: 0.9.0 has none, and the image is where scene-render publishes it.

## Consequences

- The engine reads the host's FFmpeg, Vulkan loader and fonts, as the release binary did; the image's runtime is
  used only for its smoke test. Frames matched the container's: on 33 delivered and pilot scenes, four frames each,
  31 scenes were bit-identical between 0.8.0 and 0.9.0, and the two path-traced plates differed in under 0.04 % of
  pixels (PSNR at least 77 dB), the same pixels inside and outside the container.
- Installing needs Docker and network access; running does not.
