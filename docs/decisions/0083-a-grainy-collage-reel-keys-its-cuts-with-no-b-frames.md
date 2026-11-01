---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0083: A grainy Collage reel keys its cuts with no B frames and a long interval

- Status: proposed (2026-11-01), on the Okayville coordinator's order of that day to fix the cause of a review blocker
- Deciders: the Okayville coordinator; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0076](0076-collage-two-passes-run-in-software.md) and [ADR 0077](0077-collage-keyframe-interval.md)
- Back to the [library README](../../README.md)

## Context

A non-author review of thought-of-you found Rosa's wallpaper stripes in Gary's window panes after a cut, and a mottled
frame for up to about 5 frames. Its keyframes sat at frames 0 47 94 141 160 207 254 301 306 328 375 422 434 481 528.
Its 11 cuts are at 44 77 125 158 192 246 285 306 327 368 434, so only two had a key on them, and two more had one a
frame or two late. A cut with no key is predicted from the shot before it, which is the fault.

## Cause

Encoding one lossless render of the reel with `libx264` at `medium`, as the engine does, and changing one thing at a time:

| Encode | Keyframes on the 11 cuts | Keyframes in all |
|---|---|---|
| Two passes at 5.8 Mbit/s, interval 2 s | 2 | 15 |
| Rate factor 17, 383 MB, interval 2 s | 2 | 15 |
| Rate factor 30, 2 s, grain effect removed from the scene | 11 | 16 |
| Rate factor 30, 5 s, B frames on | 5 | 12 |
| Rate factor 30, 7 s, B frames on | 4 | 10 |
| Rate factor 30, 2 s, no B frames | 9 | 28 |
| Rate factor 30, 7 s, no B frames | 11 | 14 |

The rate mode and the bits play no part: the two passes and a 383 MB rate-factor encode key the same frames. The grain
does. x264 calls a frame a scene cut when its `ratio`, one minus the inter cost over the intra cost, falls below a
`bias` that climbs with the distance from the last keyframe, from under 0.10 near a key to 0.40 at this interval. Its
debug log puts ten of this reel's cuts at 0.02 to 0.03, and the eleventh, an insert leaving, at 0.14. It also fires on
ordinary frames with no cut, at 0.10 to 0.34, because grain new on every frame costs nearly as much to predict as to
draw. So once the bias reaches that range, the frames after a cut read as scene cuts too. In the 2 s encodes, the only
keys on or just after a cut came within 22 frames of the last key.

The encoder's flash guard explains that shape: with B frames on, a scene cut followed by another is treated as a flash
and dropped. That is our reading of how x264 behaves, consistent with every row above. It was not checked against x264's
source, which this repository does not hold.

Extra-hour's scene has no grain effect, and its keys land on its cuts with the default B frames and interval.

## Decision

`collage_sketch.Staging.bframes` sets the output's `bFrames`. None, the default, writes no attribute, so every reel that
leaves it unset keeps its scene byte for byte. 0 is a setting, not the unset value. `check_staging` refuses anything but
None or a whole number from 0.

thought-of-you sets `bframes=0` and `keyframes=7.0`. On that reading, no B frames removes the guard, and the long
interval slows the bias, so the grain's ordinary frames rarely reach it. Neither alone is enough, as the table shows.
Its master has keys on all 11 cuts, and 3 others at 0, 388 and 497.

## Consequences

- The grain is unchanged, and the master stays under the posting job's 20 MB, at 17.83 MB.
- The fit is measured on one reel. x264 still decides, so a reel that sets these reads its keyframes with `ffprobe`
  against its cuts. A false key just before a cut can leave that cut without one: at 2 s with no B frames, x264 keyed
  frame 76 and logged the cut at 77, which got no key.
- The minimum spacing grows with the interval: a tenth of it, so 16 frames at 7 s. Two cuts closer than that cannot both
  get a key.
- Other grainy Collage reels at the default interval have the same fault to whatever degree their cuts show it. This
  decision does not change them, and published reels are frozen.
- `tests/test_collage_build.py` pins the unset default, the written attribute and the refusals.

## Rejected

- **A higher bitrate.** It does not move a single key, as the 383 MB row shows, and the posting job caps the size.
- **Less grain, or none on this reel.** A look is never changed to serve an encoder.
- **Forcing keys at the cut times.** It would be the exact fix, but scene-render 0.8.0's `output` has no such attribute,
  so it needs an engine change.
- **Re-encoding the engine's master outside `scene-render`.** A second generation of a grainy master, with a step
  outside the strict encode and its report.
- **A shorter interval.** It raises the bias sooner, and a fixed spacing cannot aim at irregular cuts (ADR 0077).
