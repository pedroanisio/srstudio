---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0075: A blurred far plane reaches the frame's edge, on the reels that ask

- Status: proposed (2026-10-31). Implemented: `Canvas.bleed`, `EpisodeSpec.bleed`, `collage_sketch.Staging.bleed`,
  `series.Reel.bleed`, `stick_reel.spec(bleed=)`, `look.sheet`, `look.depth(overscan=)`; `tests/test_bleed.py`.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Cutout frames carry a pale rim about 6 px wide on all four edges. On `fluent` at 5.05 s, the left edge's mean falls
from 172.1 at the outermost pixel to 102.1 six pixels in, where the same frame without the blur holds at 97.

The cause is in scene-render 0.8.0 and 0.9.0, `render_fx.rs`. A node's effect chain runs in an offscreen rectangle
clamped to the frame, unless the chain holds a warp or the node is `threeD`. What a group draws past the frame is
gone before the blur reads it, and the blur samples transparency outside its input (`effects.wgsl`). So the edge pixels
are partly transparent and the page shows. `collage_sets.OVERSCAN` draws the backdrop larger than the frame, which
is the right drawing, but the offscreen never holds the part it adds.

Measured on `fluent` at 5.05 s, mean of the left edge, outermost pixel first:

| frame | px 0 | px 1 | px 2 | px 3 | px 4 | px 5 | px 6 |
|---|---|---|---|---|---|---|---|
| as delivered | 172.1 | 156.2 | 140.6 | 126.5 | 116.1 | 107.6 | 102.1 |
| blur off | 97.1 | 96.6 | 96.9 | 96.7 | 97.9 | 97.4 | 96.9 |
| built with `bleed` | 97.1 | 96.6 | 96.9 | 96.7 | 97.9 | 97.4 | 96.9 |

Published reels are frozen, and three Okayville batches are about to land on the drawing they were built with. Their
scenes must keep every byte, because the cover fingerprint and the render's digests hold them to it
([ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md), [ADR 0040](0040-frozen-releases-at-an-accepted-drawing.md)).

## Decision

1. **A blurred far plane is a `threeD` group on a reel that asks.** The engine draws such a group on a sheet the size
   of what it draws, up to 2048 px past the frame, and blurs that. With no `<camera>` it lands where it was: the
   frame above is identical to the blur-off edge to within 0.1, and outside the outer 24 px nothing moves by more
   than one level. `look.sheet(cv)` gives the attribute. `look.depth` and `collage_sets._backdrop` use it, and so do
   the blurred groups Stick makes by hand (`stick_door`, `stick_car`).
2. **What stops at the frame also grows.** A sheet holds only what is drawn, so a far plane painted exactly to the
   frame still fades. `look.depth(..., overscan=True)` scales it about the frame's centre so its edge passes the frame
   by `look.REACH` blur radii. It is on where the measure called for it: Saga's sets, the two office angles and Rafa's
   room. It is a choice per set, not a rule of `look.depth`, because a far plane that stops above the frame's centre
   would pull away from the floor under it. Sets painted past the frame need none.
3. **It is opt-in, off by default.** `bleed` is a field of `EpisodeSpec`, and the three builders that make the spec
   for a reel pass it on. With `bleed` off, `look.sheet` and the overscan add no attribute, so every scene is the same
   document it was. New reels set it. The skill says so, on the Gloss precedent of `Reel.look = gloss_reel.LOOK`.

## Measured, by style

Edge figures are the mean of the outer two pixels along an edge, against the same frame with its blur off, at the
worst of 8 times in the reel. Page figures are the same frame on a white and a black page, mean of the edge pixels.

| Style | Scene | Before | After |
|---|---|---|---|
| Collage | `accept-all` | 46.9 | 0.1 |
| Saga | `saga-annual-review` | 4.1 (page 82 at the left edge, the page is near black) | 0.7 (page 1) |
| Cutout | `name-a-number` | 28.0 | 4.9 |
| Cutout | `out-of-cyan` | 23.9 | 8.7 |
| Cutout | `im-quitting` | 16.6 | 8.1 |
| Stick | `hold-the-door` | 11.3 | 7.1 |
| Gloss | `gloss-exit` | 0.1 | 0.0 |
| Soft | `early-night` | 0.0 | 0.0 |

The page reads 0 on the three Cutout reels after the fix, so what is left there is the blur mixing what stands next
to the edge, the wall itself being drawn past the frame. Registered sets drawn alone: News version 1 and Host each
lose an edge ramp (mean of the left edge's outer pixel 127.9 to 149.4, and 148.2 to 186.5), and News version 2 keeps
its ramp, which is its drawing. Rafa's room, painted exactly to the frame, shows 74.5 of the page with a sheet alone
and 0.1 with `overscan`. Built Toon scenes have no blurred group, and Ink and Cel draw no blur.

## Rejected alternatives

- **A default that moves for new reels by a list of old slugs.** It would spare authors the flag. A delivered reel
  missing from the list would change silently on its next build, the one failure a frozen reel cannot have, and
  branches still hold reels no list on develop knows. Forgetting the flag costs a rim, as today.
- **A zero-amount warp in the chain (`ripple`, `amount="0"`).** It also widens the offscreen and draws the same edge,
  but a warp is time-varying, so the blur is redone every frame instead of being cached: the render stage of 48 frames
  took 1.23 s against 0.83 s plain and 0.89 s with `threeD`. It also leans on an effect that does nothing.
- **An opaque underlay** (`cv.rect(g, -10, -10, 1100, 1940, ...)`, as Hiring, the party and the aisle do). It hides the
  page behind one flat colour, so the rim remains in that colour on any wall that differs, and a vignette painted in
  the backdrop stops short of it.
- **An unblurred copy of the far plane under it.** Correct colours, twice the nodes in every shot.
- **Another page colour.** A black page turned the rim dark, as measured.
- **A sub-composition larger than the frame.** It would need every far plane moved into an asset of its own, and their
  gates and keys with them.
- **Changing the engine.** The clamp is a fair default for an offscreen, and an engine change would reach every
  published reel at its next render.

## Consequences

- `look.sheet` costs one texture the size of what the far plane draws, per shot. Rendering 48 frames of `fluent` took
  the same wall time and process memory within the run's spread. GPU memory was not measured.
- A far plane with `overscan` moves. At radius 3 it grows by 2.2 %, at radius 5 by 3.7 %, so its objects sit a few
  pixels from where they sat, and a strip painted at the frame's edge narrows. Reels that opt in are drawn that way
  from their first build.
- A `threeD` group is a plane at `zDepth` 0. A reel that adds a `<camera>` for 2.5D parallax moves it with the camera.
- A reel can forget the flag. The first-delivery gates do not check it, because they would refuse the three batches
  as well.
