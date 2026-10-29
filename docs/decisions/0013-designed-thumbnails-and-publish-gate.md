---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0013: Designed thumbnails, and a publish gate that catches drift between a video and its delivery

- Status: accepted and implemented, 2026-10-28 (`srstudio.thumbnail`, `InstagramPost.thumbnail`,
  `social.take_frame`, `social.publish`, `social.check_delivery`, `episodes/instagram_posts.py deliver|check`,
  `tests/test_thumbnail.py`, `tests/test_social.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Each video is delivered for Instagram as `ig.txt` plus `cover.jpg`. The cover was a frame of the video at a chosen
time. The operator asked for an image made to act as the thumbnail, not a frame. Then they asked that the delivery
be part of the publish gate, so a video and what is published with it cannot drift apart.

Facts that shaped the design:

- The frames carry the burned-in captions and hook cards of each episode, and their characters sit at different
  places per style. A frame used as is has small text and no headline.
- The profile grid shows a cover cropped to a centred 3:4 window. That is 240 px off the top and bottom of a
  1080 × 1920 reel, and 135 px off each side of a 1080 × 1080 post.
- The engine blends in linear light. An ink band at 0.96 opacity darkened a sand-coloured frame only to about
  0.79 in sRGB terms, so burned-in captions under it stayed legible.
- Fifteen videos are delivered from one script. Re-rendering a video, or editing a post, left the old `cover.jpg`
  and `ig.txt` in place with nothing to say that they were stale.

## Decision

1. **A `Thumbnail` is data**: a headline of one to three lines, the backdrop time, a kicker, a focus point and zoom,
   an accent and a place (top or bottom). `problems()` lists every refusal, and `validate()` raises
   `ThumbnailError`.
2. **The engine draws it.** `compose` builds a one-frame scene: the frame as an image layer, scaled about the focus
   and clamped so that it always covers the cover; an ink gradient band; the kicker pill; and each headline line as
   an ink outline layer under white text. Each layer is the caption outline technique of ADR 0012. `render` draws
   it with `scene-render render` and encodes a JPEG (mode 600) through a work folder, so nothing is left behind on
   failure.
3. **The grid window is a hard bound.** The headline takes the largest size, from 200 px down to 110 px, that fits
   the window's width less a 64 px margin and keeps the kicker and lines within 38 % of the window's height.
   Otherwise the layout is refused. The band is opaque outside the window and 0.95 behind the text.
4. **Font.** The headline font is Anton 400 (OFL), installed into `generated/fonts` through `srstudio.fonts`.
   Poppins Black was rejected because its file declares the family "Poppins Black", not the "Poppins" that was
   requested, and the installer correctly refuses that.
5. **The manifest and the gate.** `publish` delivers each item that drifted and writes `delivery.json` (1.0.0). Per
   video, it records the SHA-256 of the render, a post fingerprint (caption, thumbnail spec, font, layout code) and
   the two files written. ([ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md) replaced the layout code in the
   fingerprint with the cover's drawing, and moved the manifest to 1.1.0.) `check_delivery` recomputes every entry
   and returns typed `Drift` values. The episode script exposes both as `deliver` and `check`, and `check` exits 1
   on drift. The suite runs `check` against the real delivery when `SRSTUDIO_RENDERS` and `SRSTUDIO_FONTS` are set.

## Consequences

- A re-render without a new delivery fails `check` and the gated suite. `deliver` repairs it by redrawing only the
  videos that drifted.
- Any change to `thumbnail.py` changes the fingerprint, so every cover is redrawn on the next delivery. That is
  deliberate: a layout change is a change to every published cover. (Superseded by
  [ADR 0037](0037-the-cover-fingerprint-is-the-drawing.md): only a change to what is drawn changes the fingerprint.
  A source-only edit does not.)
- Thumbnail picks (time, focus, zoom, headline) are chosen by looking at the frames. The layout guarantees fit and
  bounds, not taste.
- The gate test skips when the two variables are unset, as the fidelity test does without `SRSTUDIO_PACKAGES`. The
  documented gate command sets them.

## Addendum, 2026-10-28: delivering some videos while others wait for a render

`publish` refuses to write anything while any post has no render. Once posts are added before their videos are
rendered, that blocked the delivery of a finished video. `publish(..., only=names)` and `deliver --only NAME` deliver
the named videos alone, need only their renders and keep every other manifest entry as it was. `check` is unchanged,
so the gate still fails for each post without a render or with drift.

Rejected: skipping posts without a render in a full delivery. A plain `deliver` would then succeed while the
delivery is incomplete; naming the videos makes the partial delivery explicit.

## Rejected alternatives

- **A frame grab with text burned in by ffmpeg `drawtext`.** That is a second text renderer next to the engine, with
  no outline layering and no fit check.
- **Redrawing each episode's scene without captions as the backdrop.** Seven of the fifteen videos are built from
  packages or other styles, and one path for all of them was worth more.
- **Comparing file modification times.** They change on copy and restore, and they cannot see an edited post or a
  hand-edited cover. Content hashes can.
- **Regenerating covers automatically whenever a render changes.** That hides drift instead of reporting it. The
  gate reports drift, and the operator runs `deliver`.
