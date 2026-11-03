---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0216: A held change is keyed half a frame before its frame

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

A dance master showed a 10 Hz judder: one frame in three repeated the frame before it. Its held tracks were keyed at
`round(i / 30, 6)`. For every frame with `i mod 3 == 2` that rounds up past the frame (`2 / 30` = 0.0666666...
becomes 0.066667), so when scene-render samples frame `i` at `t = i / 30` the key is still ahead and the previous
drawing stays. Interpolated keys hardly notice a microsecond; held keys (a group's `start`/`end`, a visibility gate,
a hold or step key, a swapped drawing) change a whole frame.

Three library paths write held keys on a frame grid with that rounding: `body.BodyWindow.place` (one group per
drawing, `_body_draw.py`), `face_blends.FaceTrack.prepare` (one face drawing per frame of a blend) and
`gaze.named_gaze` (held eye states at the gaze sample times). `stick_door.shaking` keys its pose swaps at
`round(start + i / rate, 4)`, which at 12 swaps a second lands one swap in six after its frame.

Measured with scene-render 0.8.0 (`scene-render eval --frame`):

- A key at exactly a frame's sample time is shown on that frame: a gate at `repr(2 / 30)` shows the new drawing on
  frame 2, and the same gate at `0.066667` shows the old one.
- A clock offset breaks exact keys too. Inside a group with `timeOffset="1.1"`, frame 35 evaluates at local
  `35 / 30 - 1.1 = 0.06666666666666665`, before the exact `2 / 30` key, and shows the previous drawing. A key at
  `1.5 / 30` shows the right drawing on frames 34, 35 and 36.
- `body.place` on the authoring-body recipe at 30 fps showed the previous drawing on frames 2, 5, 8, ... 29, and its
  rendered frames with `i mod 3 == 2` were pixel-identical to the frame before while the body moved.

## Decision

`srstudio.held_keys` holds the rule. `held_key(time, fps)` keys a held change meant to show from `time` half a frame
before the first frame whose sample time is at or after it: `(frame - 0.5) / fps`, with a change at 0 keyed at 0.
`frame_of` names that frame, reading a time up to a hundredth of a frame after a sample time as that frame, so a
six- or four-decimal frame time still names its frame. `project_fps` reads the rate the engine samples at from a
scene's project, a whole number or a ratio such as 30000/1001.

- `body.place` keys each drawing with the canvas project's rate, so a body drawn on twos (15 a second) in a 30 fps
  reel holds each drawing for exactly two frames. Of two changes before one frame (a contact boundary and a grid
  sample), the frame shows the later, as the engine always did. A canvas whose project gives no rate is refused
  before the scene changes.
- `FaceTrack.prepare` keys frame `i` of a blend half a frame before it and draws it at `i / fps`; the blend's own
  start and end stay where they were authored, beside the pose gates keyed at the same times.
- `named_gaze` keys each eye state with the plan's `fps`. A sample rate the project rate divides (60 a second in a
  30 fps reel) keys correctly with its own rate, since every project frame is one of its frames.
- `shaking` keeps its first pose at `start` and keys each later swap with `held_key` at its new `fps` (30 by
  default), leaving out swaps no frame shows. `shaking(..., published=True)` keeps the four-decimal swap times; Hold
  the Door, published and its only caller, passes it, and its scene builds byte-identical to the published one.

`tests/test_held_keys.py` refuses any held key from these paths within a quarter of a frame of a sample time, and
asks the engine which drawing frames 0 to 11 show, with and without a time offset.

## Rejected alternatives

- Key at the exact frame time (`i / fps` unrounded). The engine shows it at global time, but any clock offset (a
  shot's `timeOffset`, a local time base) moves the frame's local time by one unit in the last place and stalls it.
- Round to more decimals. The rounding still goes up for one frame in three; only the margin shrinks.
- Fix it in the engine by sampling at frame centres. A held key exactly on a frame would then change meaning for
  every published scene, and the engine is not ours to change from here.
- Patch each call site with its own offset. The defect came from each site choosing its own key times; one helper
  keeps the rule in one place and testable.

## Consequences

New body, face-blend, named-gaze and shaking drawings show every frame its own drawing. No published episode
draws a body or a face blend or calls `named_gaze`; Hold the Door is pinned as above. Exact frame-start keys
elsewhere (the plate hosts' `runs` from 0, the composition and scene-motion raster frames, built with exact
fractions) are shown correctly at global time but would stall under a clock offset; they are left as they are
because their published output must not move, and new grid-keyed held paths use `held_keys`.
