---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0223: A held key on a shot's clock lands on the reel's frames

- Status: proposed (2026-11-03)
- Amends: [ADR 0216](0216-held-keys-at-frame-centres.md)
- Back to the [library README](../../README.md)

## Context

ADR 0216 keys a held change half a frame before the first frame at or after its time, `(frame - 0.5) / fps`, and
`Canvas(held_frames=True)` does it in `Canvas.keys`. A key with `timeBase="local"` is on its shot's clock, and
`Canvas.keys` placed it on that clock's frames. A sequence places its shots end to end, and a Stick or Saga shot
lasts as long as its voice take, which is not a whole number of frames, so most of their shots start between the
reel's frames. A change keyed half a frame before a frame of such a shot's clock lands anywhere between the reel's
frames, and the frame that first shows it is the one its time meant, the one after or the one before.

`cant-afford-to-save`, rebuilt with `held_frames=True` on develop 09bfc6a4, shows it. Shot 4 starts at 4.613271 s,
frame 110.72 at 24 fps, and cuts to a close at 2.255875 s on its own clock: 6.869146 s in the reel, frame 164.86,
which the published scene shows on frame 165. Keyed half a frame before the shot's own frame 55, at
2.2708333333333335 s, the cut landed at reel frame 165.22 and showed on frame 166. In `saga-travel-notice` the same
kind of move left frame 187 blank between CARD DECLINED and FRAUD ALERT. ADR 0216 said such a shot shows the change
"on the nearest frame, half a frame early at most"; it shows it up to a whole frame early or late.

The first-delivery gate (`held_gate.late_changes`) let those scenes through. It flagged a change written on its own
frame grid that lands within a hundredth of a frame after a reel frame, and called a change half a frame off its
own grid "meant for no frame", so a whole-frame move by `held_frames` was never late. Run over the five queued reels
rebuilt with `held_frames=True` on 09bfc6a4, the gate of this record names 247 such changes in `cant-afford-to-save`,
47 in `saga-travel-notice`, 236 in `saga-exit-interview`, 431 in `saga-take-home` and 257 in
`saga-friday-deploy`.

## Decision

A held change is keyed through its node's clock on the reel, not on the clock's own frames.

- `held_gate.clocks(composition)` gives each node under a live composition its `Clock`: where its timeline starts
  (the sequence placement the gate already does, in the engine's float order) and its ancestors' `timeOffset` and
  `timeScale` clocks. The gate reads the live `sr_core` elements through an adapter, so the canvas and the gate share
  one model of the engine's timing.
- `Clock.held(time, rate, local)` takes a change meant for `time` on the node's channel to the reel, finds the first
  reel frame at or after it (`held_keys.frame_of`'s slack), and gives the channel time that is half a frame before
  that frame, in exact fractions. A change at 0 stays at 0, and no key goes before the channel's 0. A start within a
  millionth of a frame of a reel frame, with no clock above it, is that frame, so a shot on the reel's frames keys
  exactly as `Canvas.keys` already keyed it.
- `Canvas` records each held animate it writes on a `held_frames` canvas (not inside `frozen()`), with the times it
  was asked for and the keys as written. `Canvas.place_held()` re-keys each of them through `clocks()`; of two
  changes one frame shows, the later stays. An animate removed or rewritten since the canvas wrote it is left alone,
  as is one on a node outside the composition. Placing twice changes nothing more. A timing the clocks cannot follow
  (a marker, a normalized time base, a stopped clock) is a `CanvasError` with code `canvas.held.clock`, raised
  before any key moves.
- `Episode.finish` calls `place_held()` once everything is drawn and before it checks and writes the scene. Every
  show (`toon_sketch`, `collage_sketch`, `series`, `rafa_show`, `smallprint`, `stick_reel`) finishes through it.

The gate refuses the defect. A change written within a millionth of a frame of its own half-frame grid, as a
`held_frames` canvas keys it, must land on the reel's half-frame grid, within `held_keys.SLACK`; one that lands off
it is a `Late` with `why="shot grid"`, on the first reel frame at or after it. `refusal()` says "N held changes are
keyed on a shot's frames, not the reel's, and show a frame early or late, on frames ...". Every other rule of the
gate stands.

`tests/test_held_local_clock.py` covers the `cant-afford-to-save` cut (meant for 164.86, shown on 165, stays on 165),
shots that start 0.1, 0.5, 0.72 and 0.99 of a frame past a reel frame at 24, 30 and 30000/1001 fps with changes a
twentieth of a frame after, well after and a hundredth before a frame, a shot on the reel's frames keeping its bytes,
idempotence, rewritten and removed animates, `Episode.finish`, and the engine itself (`scene-render eval`) showing
one drawing per frame in a shot that starts 0.72 of a frame late. `tests/test_held_gate.py` holds the gate's
refusal of a change keyed on a shot's frames at 24 fps and 30000/1001, and its pass when the shot starts on a frame.

## Rejected alternatives

- Place each key in `Canvas.keys`, through the node's parents at the time of the call. A shot's start in a
  sequence depends on every shot before it and on the lengths of later-drawn siblings, so it is not known until the
  scene is drawn, and walking parents needs the private `_owner` pointer of `sr_core`.
- Fix only the gate. The five queued reels would then be refused with no way to build them clean.
- Snap each shot's start to a reel frame. That moves the cut between shots off the voice take it follows and
  changes every scene with a shot between frames, published ones included.
- Change the engine to sample a shot on its own frames. The engine is not ours to change from here, and every
  published scene would change meaning.

## Consequences

A reel built with `held_frames=True` shows each held change on the first reel frame at or after its time in every
shot, wherever the shot starts. The already-built `held_frames` reels (`big-font`, `shower-argument`, and the News
pilots `five-minutes-away` and `top-that`) build byte-identical scenes with and without this change, since their
shots start on reel frames. None of the 300 scenes under `generated/episodes` is refused by the new rule. A reel
built with `held_frames=True` on an SDK before this record and not yet delivered is refused at first delivery if a
shot of it starts between frames, and is rebuilt.
