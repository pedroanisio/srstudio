---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# 0254 — Build a scene from sreditor's export

Date: 2026-11-09

Status: accepted

## Context

sreditor exports an episode as data:
- `episode.json`, with the slug, title, seed, frame, rate and language;
- `timeline.json`, a shot sequence of takes with word timings;
- a WAV per take under `audio/`;
- the bible, the beats and `style.json`.

Its render worker builds a scene from that folder and encodes it with
scene-render. The worker calls one configured command with two placeholders,
`{export}` and `{scene}`. It never runs code that comes with a job, which was
Pedro's decision of 2026-11-07, so it cannot call an episode script through
`srstudio build`.

Until now srstudio had no command that reads such a folder. `srstudio build`
runs an episode's script, and the export carries no script.

## Decision

`srstudio build-export EXPORT SCENE` writes a scene with the output id `main`.
It uses one default staging, the same for every exported style:
- the exported frame and rate;
- the stage in the background of `style.json`'s palette, or the style's own
  stage colour when the palette names none;
- each take's own audio in the mix;
- every spoken word on the engine's own caption track
  (`Episode.native_captions`), in the bundled DejaVu Sans Bold and inside the
  safe area;
- the signature cactus in the top corner, with no pot code (ADR 0001,
  ADR 0250).

`native.cues_from_takes` splits a take that would wrap past two lines into
cues at its words. The engine refused the clock captions of a long line for
crossing the safe area (SA01), although the SDK's own checks passed.

The engine resolves a scene's files against the scene's folder. So the takes'
audio and the font are copied beside the scene, at the paths the scene names.
The build runs in a temporary folder, and nothing is written when the export
is incomplete. An audio path that is absolute or contains `..` is refused, so a
timeline cannot reach outside its export. `--json` prints the result as
`srstudio.build-export/1.0.0` and sends the build's summary to stderr.

The command takes only the two arguments the worker gives. Any choice the
export does not settle is fixed here, so an export always builds the same
scene.

## Consequences

The cast and locations are not drawn. The export names drawings such as
`toon-host`, which belong to an episode's own build, and the styles' fonts are
not bundled. An episode that needs them is still built by its own script with
`srstudio build`. Drawing the bible's cast from the export is later work, and
the command's name and arguments can stay the same.

A cactus-only scene does not pass the first-delivery frame gate, which
requires both marks (ADR 0250). These scenes are reviewed through sreditor's
render, not delivered through srstudio's outbox.

## Rejected alternatives

- **Building in each exported style:** it would need fonts that are not
  bundled and drawings the export cannot supply, and would fail for most
  exports.
- **Letting the job send a build script:** this contradicts the worker's rule
  against running code from a job.
- **Writing the scene into the export folder:** the worker names the scene's
  path itself.
