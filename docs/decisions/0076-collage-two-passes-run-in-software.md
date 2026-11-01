---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0076: Collage's two passes run in software

- Status: proposed (2026-11-01), on the coordinator's order of that day to stop the caption ghost for new reels within
  the posting job's 20 MB
- Deciders: the Okayville coordinator, for the fix; written by Claude Opus 5.5 in Claude Code
- Corrects the "A smaller master" part of [ADR 0036](0036-collage-series-bible.md)
- Back to the [library README](../../README.md)

## Context

A full-size review found pale tiles on the wall and two-tone captions in Collage masters encoded at a bitrate: when a
caption left, its colour stayed behind in the flat blocks where brightness barely changed, until the next keyframe.
ADR 0036 credited a two-pass encode at 5.8 Mbit/s for those masters, and the paper grain, new every frame, for the
cost. Neither pass ever ran. `scene-render encode` picks `h264_nvenc` unless told `--hw software`, and that encoder's
arguments have no `-pass`: the engine replays the same one-pass encode twice. The file says so: its video stream is
tagged `h264_nvenc`, and it has the Main profile. So the keyframe grid, which earlier moved one ghost at the cost of
another, was never the cause.

## Decision

A Collage reel whose `Staging.bitrate` is set is encoded with `scene-render encode ... --hw software`, at the same
bitrate. The scene cannot carry this, since hardware is a flag of the command, so two things hold it:

- The `funny-reels` skill's encode step says so (1.24.0).
- `srstudio craft --renders` names the hardware encoder of a master whose scene sets `twoPass` (`craft.hardware_passes`,
  report schema 1.7.0). It reads the stream's tag with one `ffprobe`, so it costs nothing and needs no GPU.

Nothing in a scene changes, and the grain stays as drawn. Published reels, and the 64 of 31 October, keep their
masters.

## The numbers

Each caption end was sampled twice, 0.083 s and 0.25 s after it. A hit is a flat 16 px block with the luma of the raw
frame whose chroma stays nearer the frame before the caption left. All four reels were encoded through the engine, from
the same scenes:

| Reel | Length | Rate | `h264_nvenc`: size, blocks | `libx264`: size, blocks |
|---|---|---|---|---|
| book-a-table | 27.46 s | 5.3 Mbit/s | 19.44 MB, 114 | 18.72 MB, 1 |
| nail-hole | 24.17 s | 5.8 Mbit/s | 18.25 MB, 606 | 17.85 MB, 0 |
| your-lasagna | 23.17 s | 5.8 Mbit/s | 17.40 MB, 79 | 17.22 MB, 21 |
| eye-chart | 24.42 s | 5.8 Mbit/s | 18.72 MB, 681 | 18.33 MB, 0 |

The 1 and the 21 are not ghosts: the lossless encode of the same scene hits the same caption ends (17.3 and 13.6) by
1 and 21 blocks, because the master and the still frame differ by a frame where something moves.

- **The look.** SSIM against the lossless encode on book-a-table is 0.7813 in software and 0.7847 in hardware. The
  software master keeps more of the grain on a flat wall (luma deviation 3.58 against 2.92).
- **The still opening.** Mean luma drift over book-a-table's frames 1 to 10 falls from 0.108 to 0.091 on a 0-255 scale.
- **Repeatable.** Two engine encodes of book-a-table in software are the same file, byte for byte.

## Consequences

- A Collage encode takes longer: 74 s for book-a-table alone in software, against about 28 s for a one-pass hardware
  encode of it.
- The master's profile is High. `keyframeInterval` no longer needs tuning for a ghost, and a reel can leave it unset.
- A reel encoded by hand without the flag passes the encode and fails only at `craft`, which is a report and not an
  exit status. The full-size review still stands behind it.
- The Collage reels of 31 October read as hardware in `craft`, and stay as they are: the coordinator accepted their
  ghosts, to be named at delivery.
- ADR 0036's still-opening drift comparison is a comparison of two hardware rate controls, not of one pass against two.
- `GRAIN` passes `intensity`, which `film-grain` does not read (the engine's `INERT-I13`): the grain is at the engine's
  default `amount`. Changing that would change the look, so it is left as it is.

## Rejected

- **Rate factor with a cap, in software.** `crf` 26 with a 7.5 Mbit/s `maxBitrate` ran to 25.88 MB, and `crf` 28 fell to
  10.51 MB: the size follows the grain, not the reel's length, which is what ADR 0036 found for a rate factor alone.
- **`tune` and psy settings.** The engine exposes neither, and no ghost was left for them to remove. The software
  encode alone stopped it, as did every variant around it, from a 12-frame keyframe interval to `veryslow`.
- **A held grain.** The engine draws `film-grain` from the frame number and has no hold, it would change the look, and
  the bits it saves are no longer needed.
- **The ghost measure as a check.** It needs a raw frame from the engine for each caption end, so it needs a GPU and
  minutes per reel. The encoder's tag names the cause, in one call.
