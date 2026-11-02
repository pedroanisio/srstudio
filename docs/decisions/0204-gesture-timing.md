---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0204: A gesture's timing and acceleration are part of the move, measured and kept to the picture

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

A repeat is neither seen nor lost. A study window's coverage counts the distinct pictures, and a path (`hands.travel`,
`feet.travel`) is read between the seen pictures on either side of repeats, as long as those pictures lie within the
quarter beat the path is read at. On the reference, 540 of 1,507 frames repeat: 967 distinct pictures in 50.2 seconds,
19.3 a second. Counted as lost, the repeats left `hips.bounce`, `knees.bend` and `arms.height` with no window at all.

### What the samples can tell

Distinct pictures arrive irregularly: on the reference, the gap from one to the next is one frame 588 times, two
frames 254 times, three 90 times, four 31 times and five 3 times. A fit cannot hold overtones the samples cannot
tell, and a fit that tries rings between them. Read at 12 overtones, the reference's `shoulders.tilt` windows put
their peak acceleration between 146 and 1,810 amplitudes per beat squared, and one at 102,360; their fitted peak to
peak exceeded the data's own range.

`measure_dance` now keeps an overtone only where the samples can tell it, and the reading says how many it kept
(`overtones`). Three limits apply, and the lowest one wins:

- **Places.** No more than half the distinct places the samples land on in the folded cycle, as before.
- **Widest gap.** No more than `1 / (2 * widest gap)`, as a share of the cycle. Gröchenig's bound: samples no gap
  wider than that apart determine a curve of that many overtones.
- **Noise.** No overtone whose two coefficients a Wald test against the fit's own residual cannot tell from noise
  (chi-squared on two degrees, 13.8, 1 in 1,000 by chance). The highest overtone that passes sets the count.

That bound is what remains of recoverable speed and acceleration. A gesture's overtones above it are not read. Its
peak acceleration and the sharpness of its profile are then lower bounds, and at one overtone the curve is a sine,
whose timing is a sine's whatever the dancer did. In tests:

- A sine read through scatter of a tenth of its amplitude keeps at most two overtones and its peak acceleration
  within 15%.
- A whip with scatter of 1% keeps at least five, its profile within 0.05 and its fastest moment within 0.02 of a
  cycle.
- Sixteen pictures to a cycle, always on the same sixteen places, keep at most eight.

The same bound changes what repeats read as observations do to a reading. The fit takes each stop-and-double-step
for noise and keeps fewer overtones: 3 instead of 11 on the synthetic track. The profile is still 0.27 away, and the
peak acceleration is read at 133 against 342, as another gesture's.

### The study reads each channel's timing

`dance_study.ChannelReading` now carries each channel's gesture timing across its windows:

- the overtones each read window holds;
- `timed`, the windows that hold more than a sine (two overtones or more);
- across the timed windows, `peak_speed_phase` (read round the cycle, so a cluster across the hit is one cluster),
  `attack` and `release` in beats, and `peak_acceleration`;
- the mean one-cycle `velocity` and `shape` profiles from the hit, and each window's distance from the mean
  velocity profile (`profile_spread`).

The snap ratio is read on timed windows too: a sine's rise is its fall.

On the reference, the read windows' overtones are 1 at the median. Only four channels have any timed window:
`head.bob` 4 of 12 read, `shoulders.tilt` 3 of 22, `head.sway` 2 of 14, `hips.bounce` and `knees.bend` 1 each. Their
cycles do not agree either: `head.bob`'s read windows run from 0.29 to 1.1 cycles a beat, and its timed windows'
velocity profiles lie 0.29 from their mean at the median.

### The style holds it: `srstudio.dance-style/1.1.0`

1.1 adds per channel `peak_speed_phase`, `attack`, `release` and `peak_acceleration` as ranges, `velocity` (the mean
profile, 32 numbers) and `profile_distance` (how far from it a dance's may lie). It also adds `timed` to the
evidence and `repeat` to the reference's refused frames. A 1.0 record reads as before, with no timing.

A timing range stands only where all three hold:

- at least `MIN_WINDOWS` (4) windows are timed;
- the channel's trust is `good`, read in the picture's own plane, since a timing read through the estimator's depth
  guess carries that guess's jitter into its second derivative;
- for the profile, the windows agree: the 75th percentile of their distances from the mean is at most 0.15.

A check compares a phase either way round the cycle. A dance whose channel holds no more than a sine misses a timing
range as holding none.

Re-measured from the re-extracted track, `studio-hiphop` holds timing on one channel, `head.bob`:

| Measure | Range |
|---|---|
| attack | 0.32 to 0.73 beats |
| release | 1.21 to 1.87 beats |
| fastest moment | 0.82 to 0.89 of the cycle |
| peak acceleration | 4.6 to 145.6 amplitudes per beat squared |

It holds no profile, since the windows disagree. Every peak-to-peak range narrowed, because the fit no longer holds
the noise's overtones. `hips.bounce` went from 0.73..1.56 to 0.11..0.78 head radii. The snap ratio stands only on
`head.bob`, at 1.29 to 2.55.

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

### The presets keep their shapes: the reference cannot time them

A preset takes the reference's timing only where the style holds that timing for the channel the preset moves, and
the timing matches the preset's own cycle. No preset meets that, so every preset keeps its current shape:

- **The arm gestures** (`clap`, `point-up`, `raise-the-roof`, `hand-wave-side`, `arm-pump`, `arm-wave-overhead`)
  move `arms.height` and `arms.reach`. On the reference those read 1 and 2 windows, none of them timed: the arms leave
  the picture or are refused in most frames. `hands-up` holds a pose and has nothing to time.
- **`shoulder-roll`** moves `shoulders.tilt`, which has 3 timed windows out of 22, under the 4 a range needs, and
  those 3 disagree on the profile, 0.38 from their mean at the median. Its front-back roll and `shoulder-shimmy`
  read on `torso.twist`, which has no timed window and is of `fair` trust.
- **`head-nod`** moves `head.bob`, the one channel with timing ranges. Its timed windows run at 0.3 to 1.1 cycles a
  beat, mostly slower than the nod's one cycle a beat, so their attack and release in beats (0.32..0.73 and
  1.21..1.87) describe a slower head motion than a nod. Their profiles disagree (0.29 from their mean), so there is
  no profile to give it.
- **`sway` and `hip-sway`** tilt the head along `head.sway`, which has 2 timed windows. Their hips move channels the
  reference cannot time.
- **`bob`, `bounce` and `step-touch`** move `hips.bounce` and `knees.bend`. Each has one timed window and `fair` trust,
  which holds no timing range.
- **`seat-groove`** is being retuned by the separate decision on swing, and this decision does not change it.

A preset's shape changes when a reference times its channel: a recording at full picture rate, with the dancer's arms
and head in frame, read by the same study.

### A gesture is not the straight blend of its key poses

The operator's principle, stated as a test (`tests/test_dance_timing_baseline.py`). It follows a pose tracker's
holdout, which predicts a reviewed in-between from the poses around it and compares the prediction to a straight blend.
Every moving pattern of every preset is set beside the straight blend of its own key poses: the hit and the far
extreme, reached at the same moments, with a straight line between them. Its in-between must differ from the blend
in three ways:

- its velocity profile, by more than 0.15;
- its fastest moment, by more than 0.05 of the cycle;
- its attack, as a share of its own stroke, by more than 0.05.

A control checks that a straight blend fails all three when set beside its own blend.

All 69 moving patterns pass; every one is a `sine` or a `hold`. The smallest margins:

| Check | Threshold | Smallest | Pattern | Median |
|---|---|---|---|---|
| Velocity profile | 0.15 | 0.228 | `arm-pump` right arm height (sine) | 0.303 |
| Fastest moment | 0.05 | 0.055 | `step-touch` root to the right (hold) | 0.206 |
| Attack share | 0.05 | 0.148 | `step-touch` root to the right (hold) | 0.196 |

The rise is compared to within half a cycle of the highest overtone read (24), since a `hold` step is read through
that curve and no finer.

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

- A pattern can carry a measured cycle; the presets still read as before until a reference that can time them
  replaces their shape.
- Every timing reading says how many overtones it stands on. Below two, it says nothing about the gesture's timing,
  and the study and the style count it for none.
- The shipped style's peak-to-peak and snap ranges changed: they no longer hold the fit's noise.
- A curve that rings or peaks away from its hit is refused when it is read, never drawn.
