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
