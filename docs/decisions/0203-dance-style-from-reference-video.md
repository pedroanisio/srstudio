---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0203: Our dances learn a style from a reference video, as numbers only

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
whose clothes were compared and refused is never kept. A jump, a step longer than a quarter of the dancer's
height, never lands on a body smaller than 0.8 of the dancer's recent size (the dancers behind are smaller) and,
with a central pick, never lands more than a fifth of the frame's width from its middle (the camera follows the
dancer). A frame that no body passes is written lost. Every bound is a constant in the tool, never the estimator's.

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

## The reference, measured

`assets/dance/styles/studio-hiphop.json` holds the style, numbers only. Of 1,507 frames (50.2 s at 30 fps) the
tracker held the lead dancer in 1,293; the reader used 1,197 and refused 214 lost, 25 implausible and 71 jumping
frames, and dropped one arm in 187 more. Looking at the tracked frames found two short switches to a neighbour that
the tracker's rules still let through, at about 10.3 s and 38.4 s. The reader refused the first; seven frames of the
second were used (0.6% of the frames used, inside two of the 37 windows). They were left in, not edited out by hand.
The grid is the song's: 122.65 beats a minute, four to the bar, the first bar at 0.12 s.

Sizes are in head radii, angles in radians (degrees in brackets), each the middle half of the windows read, widened.

| Channel | Typical value | Swing (peak to peak) | Cycles per beat | Windows read |
|---|---|---|---|---|
| `hips.bounce` | 6.26 to 7.57 | 0.73 to 1.56 | 0.50 to 0.63 | 6 of 13 |
| `knees.bend` | 0.46 to 1.09 (26° to 62°) | 0.37 to 0.90 (21° to 51°) | 0.56 to 1.16 | 7 of 13 |
| `torso.twist` | 0.23 to 0.59 (13° to 34°) | 0.19 to 0.74 | 0.42 to 0.79 | 16 of 37 |
| `shoulders.tilt` | 0.04 to 0.35 (2° to 20°) | 0.25 to 0.49 (14° to 28°) | 0.32 to 0.69 | 24 of 37 |
| `head.bob` | 0.81 to 1.25 | 0.31 to 0.67 | 0.29 to 0.74 | 11 of 37 |
| `head.sway` | -0.29 to 0.54 | 0.47 to 1.49 | 0.26 to 0.54 | 16 of 37 |
| `arms.height` | -3.01 to 0.30 | 2.86 to 3.40 | none read | 1 of 6 |
| `stance.width` | 3.06 to 7.20 | | | |
| `hands.travel` | 2.67 to 4.67 per beat | | | |
| `feet.travel` | 1.88 to 3.38 per beat | | | |

Uncertainty, honestly: the legs are seen in about half the frames (757 of 1,197), so the leg channels rest on 13
windows and their grooves on 6 or 7; the arms are seen in 657 frames and read as a groove in one window, so only
their size and range are targets. Few windows lock to a beat, so the accent (`hit_offset`) has a target only for
`torso.roll`. The lags down the chain read zero within half a frame (about ±0.035 beats) in all 13 windows: at 30
frames a second the body moves as one block, and a lag smaller than a frame cannot be measured here.

## Findings, ranked

`tools/dance_study.py check` danced the five standing presets, the ten presets either a seated or a standing dancer
can dance, and a standing routine `choreograph` made for the song (eight bars for each preset, the whole song for the
routine) on the realistic skeleton. Every one misses the style; `shoulder-roll` comes closest, then the routine and
`hip-sway`. In order of weight across all sixteen:

1. **The hands barely move.** The dancer's hands swing about three head radii up and down in every eight-count and
   cover four to seven over it. Ours swing under 0.11 in every preset without an arm gesture, and the gestures reach
   0.6 (`hand-wave-side`) to 1.6 (`raise-the-roof`); held poses (`hands-up`, `arm-wave-overhead`) do not swing at
   all. Her hands mostly ride between level with the shoulders and three head radii below; ours hang at 5.4 below or
   stay raised.
2. **The head is fixed to the shoulders.** Her head bobs 0.3 to 0.7 and sways 0.5 to 1.5 head radii against the
   shoulders; ours bobs at most 0.15 (`bounce`) and sways at most 0.07, except `shoulder-roll`, whose sway is in
   range. (The head's typical height over the shoulders also reads about
   one head radius higher on ours, but part of that is where the estimator puts the head, between the ears, so that
   level is not a target to chase.)
3. **The shoulders stay level.** Her shoulder line tilts 14° to 28° against the hips in each eight-count; only
   `shoulder-roll` reaches that, the rest tilt 0° to 14°.
4. **The legs are straight and narrow.** Her knees stay bent 26° to 62° and swing 21° to 51° more; her feet stand
   three to seven head radii apart, and her hips ride 0.6 to 1.9 head radii lower over the ankles. Ours stand with
   straight knees (0° to 10°) and feet 1.7 to 2.1 head radii apart.
5. **The bounce has no drop.** Her hips drop 0.7 to 1.6 head radii over the ankles each cycle; ours drop 0.1 at
   most (`step-touch`), and `bounce` 0.02 with its knees bending 0.1 rad. A root bob on our skeleton barely moves the
   hips against the ankles: the legs need to fold for the hips to drop.
6. **Half time.** Her hips, knees, head and shoulders cycle about once every two beats (0.3 to 0.75 cycles a beat);
   ours lock once or twice a beat.
7. **The feet do not step.** Her feet travel 1.9 to 3.4 head radii a beat around the hips. Ours travel 1.2 to 1.4
   in the moves that move the root (`bob`, `bounce`, `sway`, `hip-sway`, `step-touch`, the routine), and that is the
   hips sliding over feet that stay put, not steps; the rest do not move them.
8. **The torso stays square.** Her shoulders sit turned 13° to 34° on the hips and twist with the groove; ours face
   front and do not twist.

## Rejected alternatives

- **Transcribing the routine into a move or a retargeted take.** It would copy the dancer's choreography, and the
  footage-derived pose would enter the repository frame by frame. Statistics over many windows teach the style and
  cannot be played back.
- **Adding the estimator to srstudio's dependencies.** MediaPipe pins its own numpy and OpenCV and ships native code
  for a step run once per reference; its own interpreter keeps srstudio's environment as it is.
- **Measuring in the picture's pixels.** The camera moves and zooms, so a pixel bob is partly the operator's hand.
  Metres from the hips, scaled by the torso, measure the body against itself.
- **Filling gaps by interpolation.** It invents motion exactly where the estimator failed, often in the fastest
  moves. Windows are read on the frames seen, with a coverage and a gap bound.
- **Following the dancer by place alone, or by colours alone.** In a class the dancers beside the lead stand close and
  wear the same grey trousers and white tops; either cue alone switched to a neighbour on the reference. Place,
  colours, and with a central pick the frame's middle after a jump, together kept her.
- **One number per channel as the target.** A single mean hides how much the dancer varies; a range of the middle
  half of the windows, widened by the noise, is a target a dance can meet without copying one window.

## Consequences

- Any of our dances, a preset, a routine or a phrase, can be scored against a measured style with one call, and the
  misses say which channel, which measure, which way and how much.
- New references need only the estimator's interpreter and a pose track under `generated/`; the repository gains a
  style record of a few kilobytes.
- Depth-bound channels (`torso.lean`, `torso.roll`) carry low trust and weigh little; a second camera angle would be
  needed to measure them well.
- Travel across the floor stays unmeasured until a reference with a fixed camera exists.
