---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0201: A move's swing is followers on springs, held to the reel's curve

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The operator judged the Stick dance proof "too dry, no curve, no swing". The seat-groove (ADR 0186) moved only the
root: a near-sine bob, a sideways snap and a shoulder shrug, every arm lag 0. Its head was fixed to its shoulders, so
the head travelled the hips' path exactly, in straight strokes eased evenly from rest to rest. Its two targets,
`SEAT_GROOVE_BOB` and `SEAT_GROOVE_SWAY`, read single channels; nothing measured the head's curve, a joint trailing
another, or a stroke that carries past its end. The operator added that the key is the timing and acceleration of each
gesture, not only its start and end poses.

### What the car reel shows

The reference is the car reel ADR 0186 measured: a third-party screen recording, 480 by 1040, of a cartoon dancing in
a car seat to a track at 129.0 beats a minute. The recording, its frames and anything derived from them frame by frame
stay outside the repository, Drive and Slack; only the numbers below are kept.

The file is a variable-rate capture of 2329 frames, but only about 1691 are distinct pictures, spaced 1/30 and 1/20 s
apart: an animation of about 24 pictures a second. One picture is about 0.09 beat, so a single picture cannot show a
lag under that; the numbers below come from fits over many cycles. The reel cuts between 24 shots, and the shots are
not locked to the music's phase, so every number is relative within a shot. Each round head was tracked as a circle
fitted to its outline, its roll read by cross-correlating the head's drawing around its centre against the shot's
median head, and the neck read as the short grey stroke under the head. Ten shots hold the groove cleanly; eight of
them agree, and the ranges below are those eight.

| Measured | Value |
|---|---|
| Head path | One loop a beat, on the beat, not half time |
| Up and across, peak to peak | 0.79..0.94 and 0.36..0.41 head radius; across over up 0.41..0.52 |
| Across against up | across's first harmonic peaks 0.16..0.20 beat before up's (the two outliers: 0.36 and 0.28) |
| Openness (area over its frame's ellipse) | 0.40..0.71, median 0.64: an open loop, not a line |
| Up strokes | down in 0.25..0.43 beat (median 0.36), up in the rest |
| Across strokes | near even, 0.44 and 0.56 of the beat |
| Head roll | first harmonic 0.2..0.45 degree: the head does not roll |
| Neck lean | about 10 to 11 degrees each way in the three clearest shots (spread about 2), 20..27 peak to peak |
| Head after the neck | +0.045, +0.056, +0.041, -0.007, +0.028 beat: +0.03 +/- 0.024, under one picture |
| Sideways rebound | 0..0.195 of the stroke, median 0.035, over 0.02 in eight shots of ten |
| Sideways speed | each stroke peaks 0.72 and 0.53 of the way through (medians); the fastest sideways travel is 0.20..0.25 beat from the bottom of the bob in seven shots of eight |
| Drop speed | peaks 0.46..0.80 of the way down (median 0.57), 0.08..0.19 beat before the bottom |

Two claims made before this measurement do not hold. The head does not tilt strongly: the drawing translates and stays
upright, as ADR 0186 said. And the hands were not measured: they rest on the sill or the wheel in most shots.

Two ADR 0186 numbers disagree with these. The bob there is 0.26..0.50 head radius; here the head travels 0.79..0.94.
The sway there snaps over in 1 part to 2.6; here the head's sideways strokes are near even. ADR 0186 read one shot's
head centroid on a cruder outline; this record keeps both targets and asks the operator which to trust (see
Consequences).

## Decision

### Followers on springs, in the move

A move gains `follows`, a tuple of `Follow(target, source, gain, lag, frequency, damping)`: the target joint moves
`gain` times its source, read `lag` beats late through the impulse response of a damped spring of `frequency` cycles
per beat. Under a damping of 1 the response overshoots and settles, which is follow-through; a lag down a chain is
overlapping action; two channels a fraction of a beat apart draw an arc. The gain carries the units: radians per head
radius when a joint follows the root.

The response is closed form and bounded: `spring` returns 48 taps over the shorter of two beats and the time the
envelope takes to fall under 1 %, normalised to sum to 1 and computed once per spring. A sample reads its source 48
times per follower; no state is carried from frame to frame, so sampling stays pure and any frame can be read alone.
A spring is refused when `damping * frequency` is under 0.3, since it would still ring at the end of its span. A
follower follows a pattern's target in the same move, never another follower, so there is no recursion; a target is
moved by one pattern or one follower; a move holds at most 32 followers. A follower counts as moving for `held`, turns
round with `mirror` (both ends mirrored, the gain's sign turned with theirs), and blends through a transition as a
pattern does.

`srstudio.dance-moves` goes to 1.1.0: a move may carry a `follow` list of objects with `target`, `source`, `gain` and
optional `lag`, `frequency` and `damping`, parsed strictly. A 1.0 document still reads; a 1.0 document that names
`follow` is refused as an unknown field, since the field did not exist in 1.0.

### Measures of swing

`measure_dance` gains `rebound`: how far the fitted cycle moves back against a stroke, as a share of peak to peak.
`measure_path(across, up)` reads a point's path on the cycle of `up`: peak to peak of each, their ratio, the `lead` of
across's first harmonic over up's in beats, the `openness` (the shoelace area over the area of the ellipse its extremes
frame) and its `shape` (`line`, `loop`, or `U` and `figure-8` when across runs at half the rate). `measure_lag`
reads how late and how large one channel follows another. `measure_swing` reads the head's path, the neck's lean, the
head's lag after it, its sideways rebound and its roll; `dance_pose.body_series` reads those channels off any dance on
any skeleton, frame by frame, refusing a pose past a joint's limit. `PathTarget` and `SwingTarget` hold a reading to
ranges and name each miss. All work on any sequence of samples, so a tracker's numbers read the same way.

### The seat-groove, retuned

```text
SEAT_GROOVE_SWING = SwingTarget(
    path=PathTarget(1.0, lead=0.18, ratio=(0.38, 0.56), openness=(0.4, 1.0)),   # lead +/- 0.06, or half a cycle round
    lean=(18 deg, 29 deg), rebound=(0.01, 0.2), roll <= 2 deg,
)
```

The lead accepts half a cycle round because the reel's left and right cannot be told from a mirror. The neck lean is
the reel's 20..27 degrees widened by its spread. `SEAT_GROOVE_BOB` and `SEAT_GROOVE_SWAY` stay as they were.

The seat-groove now drops 0.23 head radius each way, inside `SEAT_GROOVE_BOB` and nearer the reel's head, and its neck
follows the hips' slide with a gain of 2.3 radians per head radius, 0.32 beat late through a spring of 4 cycles a beat
damped at 0.75; the head follows with the opposite gain, so it rolls back against the neck and stays level. Its head
travels 0.5 head radius on a neck the same length on all three presets and the hips' slide is in head radii, so the
swing reads the same on the realistic, cartoon and stick skeletons:

| Seat-groove, each preset | Before | After | Reel |
|---|---|---|---|
| Path lead, beats | +0.428 | +0.215 | +0.16..+0.20 |
| Across over up | 0.527 | 0.44 | 0.41..0.52 |
| Openness | 0.456 | 0.71 | 0.40..0.71 |
| Neck lean, peak to peak | 0 | 25.8 deg | 20..27 deg |
| Sideways rebound | 0 | 0.102 | 0..0.195, median 0.035 |
| Head roll | 0 | 0.0 deg | under 1 deg |
| Sideways speed peak in each stroke | 0.50, 0.50 | 0.55, 0.81 | 0.53, 0.72 |
| Fastest sideways travel from the bob's bottom, beats | 0.15 | 0.23 | 0.20..0.25 |
| Head after the hips' slide, beats | 0 | about 0.25 | not visible |
| Head after the neck's lean, beats | none | -0.168 | +0.03 +/- 0.024 |

`bob`, `sway` and `head-nod` gain one follower each: the neck nods 0.14 beat after a bob's drop, the neck leans 0.21
beat after the sway's weight, and the upper chest gives 0.12 beat after a nod. With a sine source a spring shows as lag,
not as a reversal: their rebound reads 0. They have no reference.

### Speed and acceleration

The tests read the head's sideways speed off the sampled series, a fitted beat differentiated: where each stroke's
speed peaks, and where the fastest travel falls against the bob's bottom. The dry seat-groove eases every stroke at
exactly half way; the retuned one peaks late in one stroke, as the reel does. These tests do not add library timing
measures: the timing work on `feat/dance-timing` adds a `curve` waveform with continuous derivatives and timing
measures in `measure_dance` and the style check, and the two should meet there.

## Rejected alternatives

- **A routine-level swing layer**, applied over whatever a routine plays. Swing belongs to the move: a seat-groove's
  neck lean is part of that dance, and a routine layer would have to be restated for every entry and could not know
  which joint leads.
- **Overshoot in the waveform**, a pattern whose stroke carries past its end. It shapes one channel alone and cannot
  express one joint following another, which is what the reel's neck and head do.
- **A stateful spring integrated frame to frame.** Its value would depend on the frames before it, so a frame could
  not be sampled alone and two picture rates would disagree.
- **A trunk that counters the hips' slide**, so that the head moves with its neck as in the reel. The counter needed
  is the slide over the trunk's height in head radii: 0.19 radian per head radius on the realistic preset and 0.47 on
  the cartoon. One gain cannot serve both, and the swing then read differently on every skeleton.

## Consequences

- Any move can carry followers, and any character picks them up through `dance_pose`; the Stick and Toon adapters
  need no change to draw them, though they are not changed here.
- The seat-groove passes `SEAT_GROOVE_BOB`, `SEAT_GROOVE_SWAY` and `SEAT_GROOVE_SWING` on the three presets and stays
  within every joint limit.
- **Gap: the head leads its neck.** The reel's head follows its neck by +0.03 beat. The seat-groove's head runs 0.17
  beat ahead of its neck's lean, because the hips slide on the beat as `SEAT_GROOVE_SWAY` requires and carry the head
  before the neck leans. With that slide fixed at 0.2 head radius and the bob at most 0.5, a head that follows its
  neck within a picture would have to travel at least 1.6 times the slide, and its path would be wider than it is
  tall. `SEAT_GROOVE_SWING` therefore does not hold the lag. Closing the gap needs the sway moved from the hips to the
  lean, which means changing `SEAT_GROOVE_SWAY`, or a larger bob than `SEAT_GROOVE_BOB` allows; both are the operator's
  call, given the disagreements above.
- **Gap: the drop's timing.** The reel's head drops fastest 0.57 of the way down, 0.15 beat before the bottom; the
  seat-groove's drop is a half cosine, fastest half way down, 0.21 beat before. The drop is the root's channel, and
  reshaping it needs the `curve` waveform that timing work adds.
- Against the studio hip-hop style (ADR 0196) the retuned seat-groove's head now sways on its hips (0.22, 0.54 and
  0.30 head radius on the realistic, cartoon and stick presets, where it did not move before; the style's range is
  0.47..1.49), and each preset's score falls a little (realistic 25.45 to 25.19, cartoon 27.06 to 26.15, stick 28.28
  to 27.85). The sway is once a beat, where that dancer moves at half time, so its cycle is a new miss; shoulder tilt
  and arm height do not change. The two references are different dances.
