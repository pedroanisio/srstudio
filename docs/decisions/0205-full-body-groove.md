---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0205: Feet that step, a pelvis the weight drives, and a body that follows as a chain

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

The operator's verdict on every dance proof so far: "ainda está bem ruim. não tem movimento nos pés, não tem movimento
no corpo, não tem quadril, não tem ginga" (still very bad: no foot movement, no body movement, no hips, no groove).

What the code did, read before this change:

- **Moves were reviewed without the floor.** `tools/dance_views.py --moves` drew `dance_pose` alone: no held feet, no
  weight over them. Only phrases ([ADR 0194](0194-dance-phrases-on-the-floor.md)) went through `dance_floor`.
- **Nothing turned the pelvis.** No preset moved `hips.twist_left_right`; `hip-sway` tilts the hips and slides them
  over still feet, and its twist reads 0 on every skeleton.
- **A foot could not leave the floor on purpose.** A move only said which feet were planted. A free foot followed
  whatever the pose did to it and was pushed back above the floor; nothing lifted it. `step-touch`, the one move with
  footwork, lifts the free foot 0.027 hip heights, and the plants it jumps between move the hips by a step of
  acceleration: the largest change of acceleration between frames at 200 pictures a second reads 1.5 to 1.6 times its
peak acceleration.
- **The chain was one link deep.** A follower ([ADR 0201](0201-dance-swing.md)) could only follow a pattern, so a
  joint could follow the root but the chest could not follow the spine that follows the hips.

## Decision

### 1. Footwork is data, in beats

`srstudio.dance-moves` goes to **1.2.0**. A move may carry `footwork`: `strokes`, `weight`, and optional `shift`,
`inward` and `settle`. A 1.1 document reads as before; one that names `footwork`, or a follower whose source is not a
pattern target, is refused.

- A **stroke** is `foot`, `from` (beat of the loop), `beats` (at least 0.125) and a `kind`: `lift` (the whole foot,
  `height` in hip heights), `heel` (the heel rises by `pitch` radians on the ball), `toe` (the toes rise on the heel),
  `step` and `touch` (to `to`, an offset (right, forward) in hip heights from home, with an optional `height` and
  `turn`; a touch lands on the ball and holds its `pitch`), `pivot` (the foot turns on its ball to `turn` radians) and
  `return` (home). Each kind takes only the fields it uses; anything else is refused, never ignored. A stroke's
  position eases on a quintic, smooth to the acceleration at both ends, and its rise is the bump 64u³(1−u)³, which
  starts and lands at rest to the acceleration as well.
- The **weight** is a list of keys, each a beat and the share on the right foot, eased on the same quintic round the
  loop. `Footwork.check` refuses a foot that carries more than 0.02 of the weight while any part of it is off the
  floor, read at the ends of each such span and at every key inside it, and refuses a moment at which no foot stands
  flat. A dancer cannot stand on a lifted foot, so the data cannot say it.
- A foot is **planted** while it stands flat and in no stroke; the move's contacts are derived from its footwork and a
  move with footwork may not write its own.
- Each goal also says which of its **heel and toe** hold still (`FootGoal.contacts`): both on a planted foot, the toe
  alone while the heel is up, the heel alone while the toes are up, neither in the air. This is EDGE's idea of contact
  labels per heel and toe (Tseng et al. 2023, arXiv 2211.10658, section 3); no code or weights of EDGE are used. The
  slide measure below reads it.
- `inward` brings both feet in from the base stance, in hip heights; `shift` is how far the hips travel toward the
  loaded foot, a share of the way from the feet's middle; `settle` is how many beats the hips take to arrive over the
  weight, at most 0.25, so the feet and the knees move before the pelvis.
- Bounds owned by code: 32 strokes and 32 weight keys a move, an offset of at most one hip height, a height of at most
  half of one, a pitch of at most 0.9 radian, a foot turn of at most 1.2.

On the floor (`dance_floor`), a foot of the footwork is never held by the plant hold: it rides its goal. The goal
places the ball (the toes' joint, or on a foot without toes the point 0.67 of the way to its toe, where the realistic
preset's toes joint sits) and the leg is solved onto it by the existing leg solve. A heel rises about the ball and the
toes bend back so the ball does not move; a toe stroke pivots about the heel. A lifted foot is not a held foot, so it
may take the nearest turn its ankle allows; a planted foot's ankle is held to its limits as any leg is, and one it
cannot lay flat is reported, or refused when `clamp` is off. The hips sink when a foot of the footwork could not reach
its spot below them, on a ramp smooth to the acceleration, and the balance pass keys the footwork every sixteenth note,
so the centre of mass stays over the feet that are flat.

### 2. The weight drives the pelvis

The hips travel with the feet's middle and toward the loaded foot by `shift`, `settle` beats after the plan. The
source `weight` (−1 all on the left foot, +1 all on the right) can be followed like any channel: the presets follow it
with `hips.left_right` (the free hip drops), `hips.twist_left_right` (the pelvis turns after the weight), and the
bounce dips the stance knee from the stance and never rises past it, so a leg never locks straight under the bounce.

### 3. The chain, a link at a time

A follower may follow another follower or the weight. A chain is at most 8 links; a longer one, or one that closes on
itself, is refused with `dance.chain`. The sampled response of a chain is the product of its gains, the sum of its
lags and its springs convolved, binned to 96 taps, so a sample does bounded work and stays a pure function of time. A
one-link follower reads exactly as before. The presets' chain: `hips` from the weight; the trunk's tilt (spine
against the hips, chest, upper chest, neck tilt, head tilt) 0.06 beat a link; the trunk's turn (spine against the
pelvis's turn, chest, upper chest, then the neck and head turning back so the face stays forward) 0.03 beat a link;
the arms swing from the upper chest's turn, 0.1 beat late on a soft spring (2 cycles a beat, damping 0.45); the
forearms hang bent.

### 4. Three presets

| Preset | What it does |
|---|---|
| `two-step` | The right foot lands out on one, the weight rolls onto it, the left touches in on two (on its ball); the mirror on three and four. The hips dip at half time. |
| `heel-rock` | The weight rocks onto the right foot and the left heel rises; onto the left and the right heel rises; the right foot comes off the floor on the and of four. The knees take a dip on every beat. |
| `twist-groove` | The weight stands on one foot, the pelvis turns, and the free foot swivels 0.3 radian on its ball and lifts; then the same on the other foot. |

The old presets are unchanged and carry no footwork: published dances are frozen.

Chosen values, none of them measured: the study's dancer is a different dance and a different body, so only its
`torso.twist` range (0.0955..0.376 radian peak to peak, trust fair) is taken as a target. Every other value is chosen,
with its reason:

| Value | Chosen | Why |
|---|---|---|
| Lift height | 0.1..0.12 hip heights | A foot that visibly leaves the floor in every view at review size; twice the clearance target. |
| Heel pitch | 0.45 rad | The heel clears the floor by about a fifth of the foot's length. |
| Step out, touch in | 0.17 hip heights | About a foot's width: a step that reads, inside the reach of the shortest leg. |
| `inward` | 0.09 hip heights | The base stance is 0.5 hip heights wide; at that width the cartoon's ankle rolls past its limit when the weight is on one foot. 0.09 a side keeps every skeleton inside its limits. |
| `shift` | 1.0 | The hips travel all the way over the loaded foot, so the weight transfer reads. |
| `settle` | 0.1 beat | The pelvis follows the knees: with 0 the hips read 0.02 beat ahead of the loaded knee. |
| Dip | 0.14..0.15 head radii a side (0.28..0.30 deep), 0.14 for the two-step at half time | Root channels are in head radii, which are 4 times larger against the cartoon's hips than the realistic's; deeper dips tip the cartoon's ankle past its limit. |
| Pelvis tilt from the weight | 0.14 rad | Inside the target range on all three skeletons. |
| Pelvis turn | 0.2 rad a side (from the weight on the heel-rock, a pattern on the twist-groove), 0.14 on the two-step | Pelvis yaw near 0.4 peak to peak, about 11 degrees each way, so the turn reads from above. At 0.12 the turn sat at the bottom of the target and could not be seen in the top view. The two-step's larger turn jumps in acceleration on the cartoon (0.45 of its peak), so it stays at 0.14. |
| Spine against the pelvis's turn | −0.4 (−0.5 on the two-step), then the chest 0.7 and the upper chest 0.8 of the link under it | The shoulders turn back against the hips while the torso's twist stays inside the study's range. |
| Trunk links | 0.06 beat (tilt), 0.03 beat (turn) | Each link visibly later than the one under it, while the head stays within the beat. |
| Arms | 3 rad per rad of the upper chest's turn, 0.1 beat late | A swing that reads in the side view. |

### 5. Measures

`dance_groove.measure_groove(run)` reads a `dance_floor.Performance` over its whole bars, on its own skeleton, and
`GROOVE` holds a reading to its target. The timing measures of [ADR 0204](0204-gesture-timing.md) read each channel's
stroke; these read the body as a whole.

| Measure | What it reads | Target | Why this value |
|---|---|---|---|
| `clearance` | The least, over the bars, of the most the lowest sole point (heel, ball, toe tip) rises; hip heights | ≥ 0.05 | Chosen: about 5 cm on a realistic body, clearly off the floor; a raised heel with the ball down clears nothing. |
| `weight_travel` | The centre of mass's sideways travel over the mean distance between the ankles | ≥ 0.5 | Chosen: the weight goes at least half way from foot to foot. |
| `pelvis_yaw`, `pelvis_roll` | Peak to peak, radians | 0.2..0.8, 0.1..0.5 | Chosen: visible in the top and front views, short of a turn. |
| `twist` | The shoulders' line on the hips' line on the floor, peak to peak | 0.0955..0.376 | The study's `torso.twist` range ([ADR 0203](0203-dance-style-from-reference-video.md)). |
| `counter` | The twist's phase against the pelvis's turn, a share of the pelvis's cycle in 0..0.5 | ≥ 0.35 | Chosen: the torso turns back against the hips. The study's dancer twists to alternate sides, so a mean reads 0: range and phase are read, never a mean. |
| `lags` | Each link of feet (the loaded foot), knees (the loaded knee), hips, chest, shoulders, neck, head after the one under it, sideways, beats; every phase on the hips' cycle, wrapped to half of it | none ahead by more than 0.02; head ≥ 0.04 after the hips | Chosen: half a picture at 25 pictures a second and 120 BPM is 0.025 beat. |
| `loose` | The root of the upper body's variance about the pelvis's frame over its variance in the world | ≥ 0.2 | Chosen: 0 is one rigid block; `step-touch` reads 0.0. |
| `jump` | The largest change of acceleration between neighbouring frames at 200 pictures a second over the point's largest acceleration (ankles, hips, head, centre of mass) | ≤ 0.35 | Chosen: a jump in speed or acceleration reads near 1 or more; the new presets read 0.23..0.31, `step-touch` 1.5..1.6. |
| `jerk` | The mean size of the third derivative of the root's (the pelvis's) and the centre of mass's paths, m/s³ at 200 pictures a second; the larger | ≤ 500 | Chosen, at least 3 times what the new presets read (32..152), far under `step-touch` (26,000..51,000). GVHMR (Shen et al. 2024, arXiv 2409.06662, table 1) reports 12.8..16.7 for its motion estimated from video on RICH and EMDB, over 24 joints, without a formula: context only, not a measurement of ours, and a different rate and set of points. |
| `pfc` | EDGE's physical foot contact score (eqs. 9 and 10): per frame, the centre of mass's acceleration with the downward part dropped, times both feet's speeds; averaged, over the largest such acceleration. A foot's speed is its slower contact point, heel or ball, in hip heights a second | ≤ 0.01 | Chosen: a centre of mass that accelerates along the floor must push on a foot that holds still. EDGE reports 1.332 on AIST++ captures in its own units; ours is 0 whenever one foot holds, which the floor pass guarantees, so this is a guard against skating feet. |
| `slide_mm` | The farthest a held heel or toe moves along the floor from where its hold began, mm | ≤ 1 | Chosen: the floor pass holds plants to rounding. GVHMR reports 3.0..3.5 mm foot sliding for its estimated motion: context only. |

EDGE's paper (`ā` in section 4.1) keeps the horizontal acceleration and only an upward vertical one: a body falls
without a foot, it does not rise without one. EDGE used the root joint because AIST++ has no masses; ours has a
centre of mass and uses it. EDGE does not say whether the foot speeds are horizontal; we use the full speed.

## Before and after

Two bars at 120 BPM, each move danced on the floor from the class stance (`seat-groove` from the seat); misses are
counted against `GROOVE`.

| Move | Body | Clearance | Weight | Pelvis yaw | Pelvis roll | Twist | Counter | Head lag | Loose | Jump | Jerk | PFC | Slide mm | Misses |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **target** | | ≥ 0.05 | ≥ 0.5 | 0.2..0.8 | 0.1..0.5 | 0.0955..0.376 | ≥ 0.35 | ≥ 0.04 | ≥ 0.2 | ≤ 0.35 | ≤ 500 | ≤ 0.01 | ≤ 1 | 0 |
| `seat-groove` | realistic | 0 | 0.097 | 0 | 0 | 0 | — | 0.214 | 0.279 | 0.43 | 56 | 0 | 0 | 7 |
| `seat-groove` | cartoon | 0 | 0.239 | 0 | 0 | 0 | — | 0.214 | 0.243 | 0.43 | 80 | 0 | 0 | 7 |
| `seat-groove` | stick | 0 | 0.215 | 0 | 0 | 0 | — | 0.214 | 0.253 | 0.43 | 59 | 0 | 0 | 7 |
| `hip-sway` | realistic | 0 | 0.126 | 0 | 0.16 | 0 | — | -0.009 | 0.703 | 0.289 | 7 | 0 | 0 | 6 |
| `hip-sway` | cartoon | 0 | 0.427 | 0 | 0.16 | 0 | — | -0.011 | 0.42 | 1.027 | 53 | 0 | 0 | 7 |
| `hip-sway` | stick | 0 | 0.137 | 0 | 0.16 | 0 | — | -0.009 | 0.609 | 0.29 | 7 | 0 | 0 | 6 |
| `step-touch` | realistic | 0.027 | 1.215 | 0 | 0.12 | 0 | — | -0.095 | 0 | 1.507 | 49,898 | 0 | 0 | 11 |
| `step-touch` | cartoon | 0.035 | 1.451 | 0 | 0.12 | 0 | — | -0.047 | 0 | 1.575 | 26,152 | 0.005 | 3.259 | 11 |
| `step-touch` | stick | 0.028 | 1.258 | 0 | 0.12 | 0 | — | -0.088 | 0 | 1.509 | 50,924 | 0 | 0 | 11 |
| `two-step` | realistic | 0.1 | 1.357 | 0.278 | 0.268 | 0.332 | 0.46 | 0.078 | 0.334 | 0.254 | 83 | 0 | 0 | 0 |
| `two-step` | cartoon | 0.1 | 1.311 | 0.278 | 0.268 | 0.332 | 0.46 | 0.213 | 0.674 | 0.254 | 32 | 0 | 0 | 0 |
| `two-step` | stick | 0.085 | 1.364 | 0.278 | 0.268 | 0.332 | 0.46 | 0.077 | 0.292 | 0.253 | 78 | 0 | 0 | 0 |
| `heel-rock` | realistic | 0.118 | 1.008 | 0.39 | 0.264 | 0.369 | 0.46 | 0.078 | 0.342 | 0.227 | 62 | 0 | 0 | 0 |
| `heel-rock` | cartoon | 0.118 | 0.999 | 0.39 | 0.264 | 0.369 | 0.46 | 0.212 | 0.669 | 0.312 | 76 | 0 | 0 | 0 |
| `heel-rock` | stick | 0.118 | 1.016 | 0.39 | 0.264 | 0.369 | 0.46 | 0.078 | 0.298 | 0.251 | 63 | 0 | 0 | 0 |
| `twist-groove` | realistic | 0.097 | 0.965 | 0.396 | 0.269 | 0.365 | 0.418 | 0.078 | 0.333 | 0.291 | 135 | 0 | 0 | 0 |
| `twist-groove` | cartoon | 0.097 | 0.941 | 0.396 | 0.269 | 0.365 | 0.418 | 0.215 | 0.669 | 0.294 | 69 | 0 | 0 | 0 |
| `twist-groove` | stick | 0.097 | 0.973 | 0.396 | 0.269 | 0.365 | 0.418 | 0.077 | 0.293 | 0.298 | 152 | 0 | 0 | 0 |

The old presets are read as `tools/dance_views.py --floor` draws them, with the joint limits clamped: `step-touch`
passes the cartoon's ankle limits on the floor, which is also where its 3.3 mm slide and its balance findings come
from. The new presets are read unclamped and stand within every limit with no balance finding.

Against the dance study's `studio-hiphop` style ([ADR 0203](0203-dance-style-from-reference-video.md); the summed
severity of its misses, lower is closer), the old presets score 18.2..24.0 with 33..38 misses and the new ones
12.8..19.2 with 26..33. Closer, not there: the head's bob and sway, the arms' height, the hips' bounce range
and the torso's lean and roll still miss on every skeleton.

## Rejected alternatives

- **Free feet that follow the pose, lifted by a bigger pose.** A pose cannot say where a foot lands, so a step's spot
  would drift with the hips; the hold and the balance could not read it.
- **Contacts written by hand next to the strokes.** Two sources for one fact disagree; deriving them makes a lifted
  planted foot impossible.
- **A stateful spring chain integrated frame to frame.** A frame could not be sampled alone; ADR 0201 rejected it for
  the same reason.
- **Reading chain lags with `measure_lag` link by link.** Each pair picks its own cycle and a lag near half a cycle
  wraps to minus a cycle and a half; one cycle for the whole chain cannot.
- **Footwork applied to the old presets.** Published content is frozen; the new moves are new presets.

## Consequences

- Any move can lift, step, touch and turn its feet, and any character dances it through `dance_floor`.
  `tools/dance_views.py --floor` reviews moves on the floor, `--track` plays a song from its first beat and `--speed`
  slows picture and sound together.
- `GROOVE` fails `seat-groove`, `hip-sway` and `step-touch` on every skeleton and passes the three new presets on the
  realistic, cartoon and stick skeletons, within every joint limit, with no balance finding.
- **Gap: the root's units.** Root channels are in head radii, so a dip that suits the realistic body is four times as
  deep on the cartoon. The dips are chosen for the cartoon's ankle; the realistic body dips less than it could.
- **Gap: the stance is narrower than the study's.** `inward` keeps the cartoon inside its ankle limits; the study's
  dancer stands wider on the groove step. Widening needs ankle limits that allow it or a per-skeleton stance.
- Seen from above the shoulders hide the hips, so `tools/dance_views.py` draws the hip line and a tick the way the
  pelvis faces over the trunk in the top view.
- **Gap: the arms, shoulders and head move from the chain only.** The study reads them as moving too little in our
  dances; these presets give them the trunk's motion and a swing, not gestures of their own.
- Physical foot contact reads 0 on every move the floor pass dances, by construction; it guards a dance that would
  slide both feet at once.
