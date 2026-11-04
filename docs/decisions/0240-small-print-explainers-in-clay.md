---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0240: Small Print explainers are acted out in clay on Rafa's worktop

- Status: proposed (2026-11-04)
- Back to the [library README](../../README.md)

## Context

Small Print's host scenes (Rafa in his clay kitchen) hold up. Its explainers do not. A v1 explainer is a flat paper
page (`smallprint.PANELS`) with clip-art drawn on it. The v2 bar for the goldfish proof, plus the craft audit's
C1–C7, asks for these:

1. the same world as the host;
2. the subject covering at least a third of the frame, with no bare band over 20 % of its height;
3. motion every 1–2 s, with no frozen run of 1.5 s or longer;
4. real detail, such as a fish with fins and eyes that swims;
5. one short headline, then the stamp, with the source readable but secondary, and no word touching a printed
   face;
6. stills checked before any full render.

## Decision

An explainer can be a `smallprint_scene.Shot` in place of a paper panel. A `Show` takes the shots as `scenes`, and a
beat names a shot's `panel` the same way it names a paper panel.

- **Plates.** A shot draws three plates through one `plates.Camera`, all under his worktop's lights plus the shot's
  own lamps:
  - his room, out of focus (`look.depth`, moving);
  - the shot's still part on his counter;
  - one plate of the moving parts every `STEP` = 2 frames, on twos as stop motion is shot.
- **Size and camera.** The plates render at `SCALE` = 1.25 times the frame, so a push-in to 1.25 stays sharp. The
  2D camera keys (`Move`) zoom and pan about a pivot. The room moves `PARALLAX` = 0.45 as much as the worktop.
- **Checks.** `check` runs the bar before any plate renders:
  - `share`: the subject's share, from a raster of the still and moving meshes moved by the camera;
  - `empty_band`: the tallest run of rows the subject leaves bare. A row the headline or stamp crosses counts as
    covered;
  - `longest_still`: the longest run of frames with no part changing and the camera moving under 2 px at the edge;
  - `clashes`: the headline (until the stamp lands), then the stamp and its source chip, against every printed
    face (dial, calendar page), with 12 px between them;
  - the stamp stays up for at least 0.8333 s.
- **Words.** The headline is a paper chip at the top. The stamp lands in its place on the shot's word
  (`stamp_at`). Its source sits on a paper chip (`smallprint_kit.stamp(chip=True)`). With the captions, that is
  never more than two text layers.
- **Lab parts.** `smallprint_lab` holds the parts:
  - a goldfish with body, belly, scales, eyes and pupils, gill line, lips, rayed fins and a forked tail; it bends
    as it swims, its tail lags, and its beat follows its speed;
  - a lab tank with a lever, a hopper, a chute and a 24-hour timer dial;
  - a calendar whose torn page tips forward off the pad;
  - `swim` (marks eased in time), `lever`, `pellets` and `keyed` put them on the reel's clock.

## Rejected alternatives

- **Full-frame plates per frame.** One path-traced plate of the whole picture each frame costs a still-plate render,
  about a minute, per frame. The layered plates render the still part once and the moving parts in seconds each.
- **A water volume and a glass box.** A transmissive surface with the plate's clear background behind it renders
  opaque. The tank is closed instead: teal sides, a painted back, a lid. Only its front is a thin glass pane, the
  water is a thin sheet at its top, and the bubbles are opaque.
- **Keeping 2D paper pages with better drawing.** The pages stay a different world from the host. That fails bar
  point 1 and the audit's C2 (no 2D sprite inside a 3D shot, flat cards at most 15 % of runtime).
- **A low stamp under a busy top.** In the goldfish weeks shot, a stamp at row 1052 covered the fish's face. The
  stamp stays in the headline's place, and the camera keeps the printed faces below its source chip. `stamp_top`
  stays as an option, from row 236 to row 1052.
- **A calendar page that flips up over the pad.** The flipped page rose into the stamp's rows. A tear-off page that
  tips forward never rises over the pad.

## Consequences

- A Small Print show can mix paper panels and 3D shots. Published reels keep their panels.
- The bar fails before a render, so a shot that misses it costs no GPU time.
- The lab parts are `proposed` until the operator has seen them on a rendered clip.
- Each new explainer needs its own lab parts. The scene module, the checks, the stamp chip and the plate layering
  carry over.
