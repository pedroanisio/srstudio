---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0199: A gesture's timing and acceleration are part of the move, measured and kept to the picture

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The operator's direction: "The key is preserving the timing and acceleration of each gesture, not just matching its
start and end poses." It answers two verdicts on drawn dances: the stick dance's moves were "muito secos, sem curva,
sem swing", and the Toon dog's arms looked like "patas de insetos".

A pattern of [ADR 0186](0186-dance-moves-on-the-beat.md) was defined by its extremes and one of two stock shapes,
`sine` and `hold`, with a `snap` that skews where the hit falls. How a gesture moves inside its beat, where it is fastest
and how hard it speeds up and stops, was not represented anywhere.

## Decision

### A gesture's cycle is data: the `curve` waveform

`srstudio.dance-moves/1.1.0` adds a third waveform. A pattern with `"waveform": "curve"` carries `curve`, 8 to 64
samples of one cycle, evenly spaced from the hit, and no `snap`; every other pattern carries `snap` and no `curve`. A
1.0 document reads as before, and a `curve` in one is an unknown field.

The contract, enforced when the pattern is built:

- **The hit is at `u = 0`.** The first sample is `+1`, exactly, and the played curve's highest place lies within three
  eighths of a sample of it. Two samples at the top (the seam written twice) peak half a sample away and are refused.
- **Normalized.** Every sample lies in `-1..+1` and the lowest is `-1`, exactly, so `amplitude` keeps its meaning: the
  hit at `+amplitude`, the far extreme at `-amplitude`.
- **Bounded.** 8 to 64 samples: fewer cannot hold a stroke and its return with a shape of their own, more is finer than
  8 ms of a beat at 120 BPM. The reader stops at 64.
- **Finite.** No NaN, no infinity, no boolean, no text; the JSON reader refuses NaN and Infinity before the model sees
  them, and the model refuses them again.
- **Continuous across the seam.** The samples cover `[0, 1)` and the interpolant is periodic, so position, velocity and
  acceleration agree across the loop's seam by construction; a test reads all three on both sides of every sample and
  of the seam.
- **Played within bounds.** The played curve is checked on 32 places per sample: it may pass `-1..+1` by at most 0.05
  between samples, or it is refused with the advice to add samples where it turns.

### The interpolant: a periodic cubic spline

The samples are played through the periodic cubic spline: the cubic between each pair of samples whose first and second
derivatives are continuous at every sample. It is the lowest-order interpolant that keeps a gesture's velocity and its
acceleration continuous, which is the property the operator asked for: speed never jumps (no dry, mechanical start),
and acceleration never steps (no tick at a sample). Sixteen samples of a cosine play back its peak speed within 0.5%
and its peak acceleration within 2%.

### A gesture's timing is measured

`dance.measure_dance` already fitted a repeating curve to a channel and read only its extremes. Its fit is a sum of
overtones, so its derivatives are exact, and the reading now also carries, counted from the hit:

| Measure | Meaning |
|---|---|
| `peak_speed_phase` | the share of the cycle after the hit at which the gesture moves fastest |
| `attack` | seconds from 10% to 90% of the way from the far extreme onto the hit |
| `release` | seconds from 90% to 10% of the way off the hit to the far extreme |
| `peak_acceleration` | the largest acceleration, in amplitudes (half the peak to peak) per beat squared |
| `velocity` | the speed toward the hit's side over its largest, at 32 places from the hit |

`attack` and `release` leave out a rest at either extreme, which `onto` and `away` count: a `hold` rests and then
strikes, and only the strike is its attack. `dance.profile_distance` compares two velocity profiles as the root mean
square of their difference, 0 for the same gesture. A `DanceTarget` can hold any of these, with a phase read either way
round the cycle and a profile held to a distance.

The reading is band-limited: `harmonics` (1 to 32, 12 by default as before) is how many overtones the fit keeps. A
gesture whose acceleration has corners, as a spline's has at its samples, reads its peak acceleration 9% low at 12 and
5% low at 24; and the fastest moment sits on a flat top of the speed, so it reads within 0.015 of the cycle. Comparisons
between two stages read both sides the same way, so these limits cancel there.

### A repeated picture is no observation

The reference is a 30 fps screen recording, and about a third of its pictures repeat the one before. ffmpeg's
`mpdecimate` at `hi=64*4:lo=64*2:frac=0.33` keeps 587 of the first 900. Read as an observation, a repeat is a moment
of zero speed followed by a double step. That fakes acceleration spikes and moves the fastest moment, which are the
measures this decision adds. On a synthetic track with 35% of its pictures repeated, the whip read its peak
acceleration 2.6 times too high and its velocity profile 0.25 away from the same track without repeats.

`srstudio.pose-track/1.1.0` therefore records repeats. Each frame says whether its picture repeats the last distinct
one (`repeat`). A repeated frame carries its clock and no landmarks, and the first frame cannot repeat. A `1.0.0`
record reads as before, every frame its own picture.

`tools/pose_extract.py` applies the same test per 8 x 8 block of grey levels, against the last distinct picture. It
writes a match as a repeat without running the estimator, and the tracker does not step on it.

The study counts a repeat as not seen (`BodyTrack.repeats`). Its jump check spans repeats, scaled by the real time
between the two distinct pictures. `measure_dance` fits each channel on the frames seen, at their real times, so
nothing is differentiated across a repeat. With the repeats left out, the same synthetic track measures within a
profile distance of 0.001 and 0.5% of its peak acceleration.

What remains is a bound, not a bias. Distinct pictures arrive irregularly, at about 20 a second, and a fit can only
hold the overtones they cover. `measure_dance` already limits its overtones to what the samples' places in the folded
cycle can tell, and a reading carries the widest gap they leave.

### A gesture's timing is kept to the picture

`tests/test_dance_timing_stages.py` follows one gesture, a whip on the right upper arm (a slow lift and a strike back
onto the hit in a quarter of the beat), through every stage between a move and a drawn picture, and measures it the
same way at each:

| Stage | What it does to the gesture's clock | Held |
|---|---|---|
| `dance.sample` -> `dance_pose` | adds the move's value onto the base pose | exactly |
| skeleton | one control turns the hand round a fixed axis: the hand's speed is the control's times one radius | to 1e-6 |
| clip -> `retarget.perform` | plays the clip's frames on the song's clock through a beat map | see below |
| `tools/dance_views.py` | keeps two of the world's three axes | exactly |

Two parts of the retarget stage bent the gesture, and both are fixed at their cause:

- **Between frames, a straight turn.** A performance slerped each joint from one frame to the next, so speed was
  constant between frames and stepped at each one, and acceleration became a spike at every frame. A clip of the whip
  at 30 frames a second, played at its own tempo, read its peak acceleration 2.7 times too high (411.7 against 150.5
  amplitudes per beat squared) and its fastest moment 0.04 of a cycle late. A performance now reads every frame into
  the character's controls once and plays each control, and each axis of the hips' place, through the natural cubic
  spline of its frames: continuous to the acceleration, exact at every frame. The same clip now reads its peak
  acceleration 1% low and its fastest moment within 0.008 of a cycle. Between frames the spline stays within 0.002
  radians of the slerp on the reference walk. Played in controls, not turns, a two-control joint such as a knee no
  longer leaves its axes between frames. A control the spline carries past a limit that both frames keep is held at
  the limit and not counted, since the clip never put it there; past a frame's own limit it is held and counted, or
  refused, as before. `to_pose` at a single time keeps the slerp: one moment has no neighbours to curve through.
- **At each beat, a step in rate.** A beat map ran straight between beats, so where two stretches of a take had
  different rates every gesture in flight stepped its speed at the beat, and its acceleration spiked there. The rate
  now eases from one stretch's to the next. Over a stretch of mean rate `R` it is `R + a phi(tau) + b phi(1 - tau)`
  with `phi(tau) = 1 - 18 tau^2 + 32 tau^3 - 15 tau^4`, which is 1 at the stretch's start, 0 at its end, flat at
  both, and integrates to 0. So every beat lands exactly on its beat, every stretch keeps its mean rate, the rate is
  continuous at each beat and its change continuous too, and the change is bounded (`BeatMap.max_rate_change`). The
  rate at a beat is the mean of its two stretches' rates where each has room for it. A stretch moves its rate by at
  most half its room inside 0.5..2.0 at either end, so the instantaneous rate never leaves that range. Where two
  neighbours are too far apart for that, the rate steps at that beat by what is left, which is always less than a
  straight map's step. The first and last beats keep their stretch's rate, so the map still runs straight past the
  ends. `song_time` turns a clip second back by Newton steps guarded by bisection, at most 64.

A take whose beats fall unevenly, with its tempo easing between them as a dancer's does, plays the gesture on the
song's even beats with its timing and acceleration kept. On such a take at 30 frames a second, the arm's speed stepped
at a beat by up to 48% of its top speed, from the frame corners and the rate steps together. It now steps by under
0.1%, which is the finite difference's own error. How well a take holds a strike's peak acceleration is the
take's own limit, not a stage's. The whip's strike lasts under four frames at 30 frames a second, and on uneven beats
those frames fall at a different place in each cycle, so they hold its peak 10% low at 30, 3% low at 60 and 0.1% at
120.

The drawing adapters of the stick and Toon styles are not on the base this decision was made on. Each draws a
skeleton pose sampled at its own picture times. Their own stage test belongs with them: the same gesture, measured at
their pictures, held to the source.

## Rejected alternatives

- **Linear interpolation between samples.** Speed is constant between samples and jumps at each one; acceleration is a
  train of spikes. It is the dry motion the operator rejected.
- **Catmull-Rom or a monotone cubic (PCHIP).** Both keep speed continuous but step acceleration at every sample, and
  PCHIP flattens a gesture's extremes to keep monotone runs.
- **A Fourier series of the cycle.** Smooth everywhere and periodic, but its coefficients are not readable as poses,
  and a sharp strike rings across the whole cycle instead of near the strike.
- **A cubic B-spline through control points.** Continuous to the second derivative and free of ringing, but it does not
  pass through its points, so the hit would not land at `+amplitude` on the beat.

## Consequences

- A pattern can carry a measured cycle; the presets still read as before until a measurement replaces their shape.
- A curve that rings or peaks away from its hit is refused when it is read, never drawn.
