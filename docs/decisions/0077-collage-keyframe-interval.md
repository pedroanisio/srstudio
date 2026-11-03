---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0077: A Collage reel may set its keyframe interval

- Status: proposed (2026-11-01), on the Okayville coordinator's order of that day to record `Staging.keyframes`
- Deciders: the Okayville coordinator; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0036](0036-collage-series-bible.md)
- Back to the [library README](../../README.md)

## Context

A full-size review of book-a-table found a pale square on the wall that the raw frame does not have. Where a caption
leaves with no cut, and its blank end is about as bright as the wall, the colour of its pill stayed in the blocks it had
covered until the next keyframe. The engine's default puts a keyframe every 2 s, and neither of this reel's two
uncut caption exits landed near one.

## Decision

`collage_sketch.Staging.keyframes` sets the seconds between keyframes on the reel's main output, as
`keyframeInterval` to four decimals. 0, the default, writes no attribute, so every reel that leaves it unset keeps its
scene byte for byte. `check_staging` refuses a negative number, a non-number and NaN with a `StagingError`.

book-a-table sets `52 / 24`, which puts keyframes on frames 416 and 624: her caption leaves on the first, and the last
one leaves just before the second. It is the only reel that sets one.

## What it does not do

The interval did not stop the ghost, and it is not the fix. It was chosen while the masters came from `h264_nvenc`,
which `scene-render encode` picks unless told `--hw software`. Both book-a-table masters below come from the same scene,
which sets the interval. A hit is a flat 16 px block that keeps the chroma of the frame before a caption left, sampled
twice per caption end:

| Encoder | Size | Blocks | Caption ends with 4 or more |
|---|---|---|---|
| `h264_nvenc` | 19.44 MB | 114 | 4 |
| `libx264` | 18.72 MB | 1 | 0 |

A later reel that needs a clean caption exit gets it from the encoder, not from this field.

## Consequences

- book-a-table's scene keeps the interval, so changing it would mean rebuilding that reel.
- The interval is whole-reel: it cannot aim at more caption exits than one spacing lands on.
- At this interval the reel stays under the posting job's 20 MB in both encoders.
- `tests/test_collage_build.py` pins the unset default, the written attribute and the refusals.

## Rejected

- **A shorter interval on every reel.** It changes the scene of every Collage reel, and published reels are frozen.
- **Moving the captions onto the existing keyframes.** Caption times follow the takes, so this would change the reel's
  timing to serve an encoder setting.
- **Writing the attribute in the reel's own code.** The output is built in one place, and a field there is checked and
  tested once for every reel.
