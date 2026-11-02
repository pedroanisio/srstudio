---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0160: Ink on moving 3D is drawn from an id pass and measured between frames

- Status: proposed (2026-11-01)
- Deciders: the operator; worked out with the srlocations looks owner; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0091](0091-hybrid-drawing-is-the-default.md) and [ADR 0098](0098-wire-vehicles-as-props.md)
- Back to the [library README](../../README.md)

## Context

The 3D pilot of ADR 0098 paints over its world with one post shader, `episodes/pilots/paint.glsl`: a Kuwahara filter,
light bands, then Sobel ink on the brightness of the finished picture. Ink from brightness traces whatever is bright
or dark, including the strands of a beard, a puffer's quilting, texture and cast shadows, and it misses an edge
between two surfaces that happen to be equally bright.

srlocations draws a set once per pass in one document: a group's 2D effects apply to the 3D inside it, so an unlit
group of flat id colours under `ink.fs` inks where one surface meets another, whatever the light does. Nothing measured
whether such lines hold still while a camera moves, which is what decides if a paint-over can move at all, and nothing
built or compiled the pilot's shader in a test.

## Decision

- `srstudio.ink_pass` builds the id pass inside an existing scene. It copies each visible object of a 3D group into a
  group straight above it, in an unlit and double-sided colour keyed by what the eye reads as one surface. A primitive
  keeps its own colour. Meshes on one parent share one per material family. Copies stay parented to the rig objects the
  originals use, so the keys exist once and the passes cannot drift. A refused pass leaves the scene unchanged.
- The ink shaders are vendored from srlocations into `src/srstudio/assets/shaders`, with the source commit and each
  file's SHA-256 in `vendored.json`. There is no Python import between the projects. `tests/test_shaders.py` checks the
  pin and compiles each shader, and the pilot's `paint.glsl`, on the real engine.
- Every render of a shader runs with `--strict`. Without it, engine 0.8.0 passes a shader that fails to compile
  straight through, draws the frame without it, and exits 0.
- `srstudio.line_stability` measures lines between frames from an inked folder and a plain one. It reports:
  - popped ink: ink with no ink near it in the next frame;
  - unexplained ink: popped ink left over once motion read from the plain frames, and half a block to each side, is
    allowed for;
  - specks, and popped ink sorted by the width of the region it outlines;
  - stroke widths along chosen rows and columns, with their reversals, and the swing of the frame's ink total.

  `tools/line_stability.py` runs it on any frame folders.
- `wire_mesh` winds every closed piece of a model out of its own volume before it falls back to the car's or the
  jet's outward rule. A seat read from the car's centre line was half inside out.

## Measured

These were measured on the 3D pilot's scene with its finish removed, at five frame pairs per shot, on engine 0.8.0.

- **Doubled faces.** The seat stair-steps came from faces missing in the id pass only. The pilot's materials are
  double-sided and the id materials were not, so wrongly wound faces drew lit and vanished from the ink. Both fixes
  above remove them.
- **The line across the face.** It came from the scalp mesh, which covers the upper face, being keyed as hair. A
  family follows how a surface looks, not its material's name, and a table of families needs a look at the frame.
- **Popping.** With unexplained ink as the measure, id ink and Sobel ink are level on the cockpit shot, at 0.08% and
  0.14% of ink, and close on the wide shot, at 1.78% and 1.04%. Sobel holds better on the car close-up, at 0.09%
  against 1.06%. Ink on id regions under 4 px wide almost never popped, so thin regions are not the cause.
- **Exact key times.** Writing key times as exact multiples of the frame made no difference to popping on this scene.
- **Width chatter on a slow dolly.** This is the look risk the operator's sofa-room push showed. With the engine's 3D
  antialias on, the pixels of an id edge are blends that the ink treats as a third colour. A line's width therefore
  depends on where the edge falls inside a pixel, and it turns back and forth from frame to frame. Turning
  `antialias3d` down to 1 cut reversals from 49 to 11 on one row of a test table at supersample 1. A line still steps
  by a whole pixel. Supersampling shrinks the steps but does not stop them reversing. With antialias on, the worst
  width change fell from 1.99 px at supersample 1 to 0.99 px at 2 and 0.66 px at 3, while reversals rose from 49 to
  105 and 135. A sub-sampled variant of `ink.fs` did not change either result, because a shader reads its input
  texel by texel.

## Consequences

- Width chatter is measured but was not visible at playback: on the sofa-room push, Pedro's verdict was "no shimmer,
  the move passes" (arc4d3, Slack 1793582912.027519). `antialias3d` stays as it is, and no look is traded for the
  measure. The width read stays a tool, `tools/line_stability.py --rows`, and not a failing test. If chatter becomes
  visible, the measured lever is the id pass's antialias. That setting is project-wide, so turning it down also
  aliases the lit picture. The ink shader is srlocations' to change, and only behind an opt-in setting.
- `paint.glsl` stays the pilot's shader. A moving reel's look is chosen on the measures above and on a rendered clip,
  not on stills.
- A changed vendored shader is a new pin and a new commit. The compile test fails until both agree.

## Alternatives

- **Sobel on the finished picture.** It is cheap and holds steady on a close-up, but lines follow brightness, not
  surfaces. It stays available where that suits a style.
- **Sharing shaders through the srlocations catalog.** The catalog's `exchange.allowed` admits catalog records, `files/`
  and `models/`, not loose `.fs` sources.
- **Comparing raw pixel change between frames.** That counts every real movement as flicker. Motion read from the plain
  frames removes it, and the measure says where it cannot: behind something that moved in front, and past its search
  reach.
