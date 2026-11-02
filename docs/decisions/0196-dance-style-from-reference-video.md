---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0196: Our dances learn a style from a reference video, as numbers only

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

Our presets (ADR 0186, 0192) and routines (ADR 0193) prove timing and joint limits; nothing yet says whether they move
like people who dance. The operator supplied a reference: a recording dated 2026-11-02 of a hip-hop dance class, about
50 seconds, a handheld camera following a dancer at the centre of a group, the song at about 122.7 beats a minute.
We want to learn from how the dancer moves without copying what she dances.

Three constraints shape the answer. The people in the recording are real, so the footage, its frames and anything
derived from it frame by frame (stills, overlays, per-frame landmarks) stay out of the repository, Drive and Slack.
A pose estimator is a model whose output is wrong in ordinary ways (a neighbour taken for the dancer, a limb read
through the body, a frame of noise), so its output is untrusted. And the camera moves, so nothing measured against the
picture is a measure of the dancer.

## Decision

Measure style, not choreography: statistics of how each part of the body moves against the beat, taken over many
eight-count windows. Only those statistics enter the repository, as ranges; a routine cannot be rebuilt from them.

### Extraction, outside srstudio

`tools/pose_extract.py` runs MediaPipe's Pose Landmarker (Apache-2.0; the heavy model, its digest pinned in the tool)
in its own interpreter under the workspace's `generated/venvs/pose` (directory 700), so srstudio gains no dependency.
It writes a `srstudio.pose-track/1.0.0` record only outside the repository (directory 700, file 600), after
`srstudio.pose_track` has parsed it. The record carries the schema, the tool, the estimator's name, version, model
digest and licence, the source's digest, size, frame rate and frame count, how the dancer was picked, and per frame
the 33 landmarks in the image (with visibility and presence) and in metres from the hips, the dancer's box, and how far
the dancer moved and how unlike their clothes looked, or nulls for a lost frame.

The tool follows one dancer, the most central large body or the one nearest a given point. Each frame it asks the
estimator for up to five bodies in the whole frame and one in a crop around where the dancer should be. It keeps the
dancer by place, a jump measured in body sizes from the predicted place, and by the colours of the clothes, torso and
legs compared separately against the mean of the first fifteen matches, learned slowly after that. A body whose
clothes cannot be compared is kept by place alone for at most 45 frames, and only with no other body near it; a body
whose clothes were compared and refused is never kept. A frame that no body passes is written lost. Every bound is a
constant in the tool, never the estimator's.

### The reader: `srstudio.pose_track`

A strict parse: unknown or missing keys, duplicate keys, non-finite numbers, a version other than 1.x, frames out of
order or off their clock, landmarks out of range, a found frame missing a part, a lost frame holding one, and records
over 64 MB or 36,000 frames all raise a typed `PoseTrackError` at a path. The module uses the standard library only,
so the extraction tool loads the same parser in the estimator's interpreter.

### The body: `srstudio.dance_study`

`reference_body` keeps thirteen points that both the estimator and the canonical skeleton place (hips, knees, ankles,
shoulders, elbows, wrists, the head's centre), in the skeleton's axes, from the hips' middle, scaled so the torso is as
long as the realistic preset's (4.8 head radii). Starting at the hips and scaling by the torso remove the camera's
travel and distance; the camera's tilt remains, and the channels it reaches carry a lower trust.

Frames are refused and counted by reason: `lost`, `low_confidence` (a hip or a shoulder seen under 0.5), `implausible`
(a leg or torso bone 1.5 times longer or shorter than its own median), and `jump` (a point moving more than three head
radii in a thirtieth of a second). A misread arm is dropped from its frame alone and counted under `arm`. Nothing is
interpolated: a channel is measured on the frames where it is seen.

`dance_body` turns any `DanceFrame` sequence (a move, a routine, a phrase) danced on a preset skeleton into the same
body, so our dances are measured by the same code. `pose_record` writes one of our dances as a pose-track record, for
the round trip and for tests that hold no real person.

### The measures

`measure_style` reads thirteen channels on the beat grid, each in windows of eight beats every two beats. A window is
read when it sees 60% of its frames and no gap is longer than a beat; `dance.measure_dance` fits the groove on the
frames seen (it now accepts missing samples). Per window it keeps the size (peak to peak), cycles per beat, the snap
ratio, where the accent falls against the beat, and the range covered.

| Channel | Unit | Trust | Why that trust |
|---|---|---|---|
| `hips.bounce` | head radii | fair | the hips' height over the lower ankle; a lifted foot reads as a drop |
| `knees.bend` | rad | fair | the knee's angle; depth blurs a knee bent toward the camera |
| `torso.lean` | rad | poor | forward lean is mostly depth, and the camera's tilt adds to it |
| `torso.roll` | rad | poor | the camera's roll adds to it one for one |
| `torso.twist` | rad | fair | shoulders against hips, seen in depth |
| `shoulders.tilt` | rad | good | the shoulders' line against the hips' line, both in the picture |
| `head.bob` | head radii | good | the head's height over the shoulders |
| `head.sway` | head radii | good | the head sideways over the shoulders |
| `arms.height` | head radii | good | the hands' height over the shoulders |
| `arms.reach` | ratio | fair | shoulder to wrist over the arm's length; depth hides a reach toward the camera |
| `hands.travel` | head radii per beat | fair | the hands' path around the hips, quarter-beat steps |
| `feet.travel` | head radii per beat | fair | the feet's path around the hips |
| `stance.width` | head radii | good | ankle to ankle |

It also reads the lag of motion down the body's chain: hips to chest, chest to head, hips to head and chest to hands,
from the peak of the masked cross-correlation of vertical velocities within half a beat, refined between frames, and
read only when the correlation passes 0.3. `root.travel` across the floor is not measured: the camera follows the
dancer and the estimator's metres start at the hips, so nothing in the picture is fixed to the floor.

Uncertainty is reported, never hidden: each measure is the spread of its windows (10th to 90th percentile), each
channel carries its noise (the median absolute residual of a five-frame quadratic fit, so a smooth swing is not
noise), and the evidence (frames, windows, windows read, still, locked to a beat) travels with every target.

### The style record: `srstudio.dance_style`

`derive` turns a reading into a `srstudio.dance-style/1.0.0` record of ranges: the middle half of the windows, widened
by twice the noise and by at least half the unit's floor (0.05 head radii, 0.03 rad), cycles by 0.05, the accent and
the lags by half a frame, the ends rounded outward. A measure read from fewer than four windows has no target. The
record names its source by digest and description only, its estimator, the counts of frames used and refused, the
grid, the generator, and what it could not measure. `parse_style` is strict in the same way as the reader: channels
and lags in their fixed order, units and trust checked against the channel, ranges ordered and inside each measure's
limits, evidence consistent, level-only channels without groove ranges.

`DanceStyle.misses(reading)` lists what a dance misses, ranked by severity: the channel's trust (good 1, fair 0.6,
poor 0.25) times the measure's importance (level and size 1, range and lag 0.8, cycles 0.7, accent 0.6, snap 0.5)
times how far outside the range it falls in range widths, capped at four. A dance that shows no steady cycle where the
reference has one misses at the full weight. `dance_style.check(style, frames, groove, fps)` measures any `DanceFrame`
sequence on the realistic preset and returns the misses and their summed score. Shipped styles live in
`assets/dance/styles/` and load with `dance_style.styles()`.

`tools/dance_study.py` runs it: `measure` writes the style from a pose track and the song's grid, `check` dances every
standing preset for eight bars and a routine `choreograph` makes for the song, and ranks the misses they share, and
`page` writes the operator's local proof page (in Portuguese) beside the footage under `generated/`.
