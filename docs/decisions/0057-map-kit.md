---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0057: the map kit

- **Status:** proposed
- **Deciders:** Pedro (operator)
- Back to the [library README](../../README.md)

## Context

A new channel of reels about the world on a map needs a globe, flat maps, labelled pins and parallels, a camera, a
population layer and a circle with a total. A label on a map is a claim with a number in it, so a pin, a line and a coast
have to be placed by one projection and stay right while the camera moves, and a figure on screen has to be traceable
to its dataset. The reels have to stay bright and moving: the first round of Mind pilots failed on low brightness and
motion.

## Decision

- `srstudio.map_kit` holds the channel. `MAPS` is Toon on its own clock, master and letters (Lexend 800), and
  `MAPS_CAST` adds a card, so a map shot stages as a Mind card shot does. `NARRATOR` is the channel's own constant.
- The pictures are the engine's native `<map>` asset, in three named views: `globe` (orthographic), `flat`
  (equirectangular) and `equal_area` (Lambert azimuthal equal-area). Pins and tags ride the map through `geo()`
  expressions, so they cannot drift off the projection.
- A size on screen is a formula, never a measurement of the picture. `ring_px` is the Lambert chord `2R sin(r / 2R)`.
  Rendered against a dense native route of a 3,300 km small circle at a target of 430 px, the line measured a median of
  429.9 px from the frame's centre, at both Mong Khet and Adelaide.
- `equal_area` re-centres along a great circle (`glide`) under a screen-fixed ring, so one ring is the same circle on
  the Earth at every frame of a move.
- `Place` holds the gazetteer's number and rounds it in one place, and refuses a name that does not say which place it
  is, such as "New York". `check_labels` refuses more than six labels at once and `check_copy` reuses Mind's list.
- The layers are small derived files in `src/srstudio/assets/maps/`, built by `tools/maps/build_layers.py` from Natural
  Earth 1:50m (pinned at v5.1.2) and GHS-POP R2023A, with every input's SHA-256 in `layers.json`. A clean checkout
  builds a reel without the population grids, which stay outside git.
- Population is dots, one per million people, in three zones (inside the Mong Khet circle, inside the Adelaide circle,
  neither). A zone holds its total in dots, rounded to the nearest million, so a zone can be counted, and each dot
  falls near the people it stands for.
- New parts stay `proposed`.

## Rejected alternatives

- **Pre-rendered raster maps.** They would be simple to composite, but a pin would have to be placed by a second copy
  of the projection, and every zoom would need a new render or a soft upscale.
- **A heat map of the population grid.** It is smoother, but it needs a raster asset far larger than the dots, and a
  colour ramp says "more" where a dot can be counted.
- **Natural Earth 1:10m.** Its coast is finer than any zoom the reels use, at many times the size in git.
- **Mercator or a true-scale circle on a flat map.** Mercator inflates the far north, and a circle of fixed radius is
  not a circle on an equirectangular map. Lambert is the view whose circle and areas are both honest.

## Consequences

- The layers add about 1.7 MB to the package.
- The large lakes are holes in `land`, not a layer of their own. A layer with nothing in frame is a finding the strict
  encode refuses, and an ocean holds no lake; a hole is drawn wherever the land is.
- A fast flight over a flat map swaps land and sea over most of the frame, which the strict encode refuses as a flash.
  So the same map is laid over itself, heavily blurred, for the fast part of each flight of 0.3 s or more, and the map
  carries no film grain, whose frame-by-frame change the same check counts.
- Antarctica's outline loses the points Natural Earth runs along latitude -90, which an azimuthal view draws as a line
  across the ice. It and the lake holes are the only changes to a Natural Earth shape besides rounding.
- `specimens.DRAWN` classifies the map elements, so a map part has a fingerprint like any other. A recipe gets the folder
  it renders in through `Context.work`, because a map reads its layers beside the document.
- The population layer's zones are named after two circles, so a reel about a third circle needs a rebuilt layer.
