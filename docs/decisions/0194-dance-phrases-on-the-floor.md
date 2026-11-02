---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0194: Counted dance phrases travel and turn on a floor that holds the feet and the weight

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

A `dance.Move` ([ADR 0186](0186-dance-moves-on-the-beat.md)) is a loop of waveforms on joints: a bob, a sway, an arm
gesture. A hip-hop class routine is not a loop. It is counted in eights ("five, six, seven, eight", with the "and"
between), each count lands a shape, the legs step, kick and sink, the body travels across the floor and turns, and a
room of dancers does it together or in canon. Three things the move model cannot say are needed for that:

- key poses on counts, legs included, with how each one arrives: struck on the count or eased;
- travel and turns of the whole body over the floor, with planted feet that do not slide while it moves;
- weight: a dancer standing on one foot has the body over that foot, or falls.

## Decision

### A phrase is a sibling of a move

`dance.Phrase(name, eights, keys, description)` holds `Key(beat, contacts, pose, ease, floor, airborne,
expression)` poses. It is a sibling of `Move`, not a kind of move: `Entry.move` is `Move | Phrase`, and `dance.sample`,
`dance.frames`, `Routine`, `dance_pose` and `choreograph` take either.

- Counts are `EIGHT:COUNT` with an optional `e`, `&` or `a` (`"2:5&"` is beat 12.5); `beat_of` and `count_of` convert,
  and a key lies on a sixteenth of a count. A phrase is 1 to 16 eights of at most 256 keys, the first on `1:1`.
- `pose` is canonical targets (legs included) in radians, a joint left out at zero; `root.*` is refused, because the
  body moves with `floor`.
- `ease` is `smooth` (eases out and in), `linear` (one speed, for travel) or `hit` (holds, then strikes onto the key in
  the last `HIT_SHARE` = 0.35 of the span). Between keys every channel moves on the later key's ease.
- `Floor(right, forward, up, turn)` is where the body stands from where the phrase started: travel in **hip heights**
  (pelvis height) in the frame the dancer faced at the start, the hips' rise in hip heights, the turn in radians about
  the vertical, positive to the right. Hip heights scale with the legs, so a cartoon whose head is a quarter of its
  height takes the same steps as a realistic figure. Head radii, which moves use for a bob, would make the cartoon's
  steps three times too long for its legs.
- `contacts` names the feet that carry the body at the key. Between two keys a foot carries it only when both name
  it: a foot leaving at the next key lifts as soon as this one is passed, and a foot landing at the next key lands on
  it. Two keys with no foot in common are refused unless one is `airborne` (a jump, no contacts); the first and last
  keys stand on the floor.
- A `Routine` holds a phrase a whole number of times; each time starts where the last left the body
  (`Floor.then`), and rest after it keeps the body there. A phrase crossfades with a move by weight; the floor's rise
  crossfades with it.
- `srstudio.dance-phrases/1.0.0` is the file: a strict reader (`parse_phrases`, `load_phrases`) refuses unknown
  fields, wrong types, non-finite numbers, more than 64 phrases or 256 keys, and a floor channel a key leaves out
  holds the key before's value. `dance.phrases()` reads the shipped file.

**Rejected: a phrase as a kind of move.** A `Move` is a loop: patterns with a period, `loop_beats`, an intensity that
scales amplitudes, and a parameter crossfade that blends two moves' waveforms. A phrase has none of these; it has
keys, an ease, travel and contacts that change within it. Folding it in would make every one of those fields optional
on one class and every consumer branch on which half is set. Two types with one sampling contract (`DanceFrame`) keep
both honest.

### The floor pass (`srstudio.dance_floor`)

`DanceFrame` gains `floor` and `airborne`; `dance_pose` moves and turns the base pose's root by the floor.
`dance_floor` then puts any dance on a floor, for any style:

- `perform(phrase_or_routine, profile, groove, *, spot, base, delay_beats, clamp, balance, strict, fps, margin_m)` →
  `Performance` with `pose(t)`, `sample(t)` → `FloorFrame`, `frames(fps)`, `slip(fps)`, `balance(fps)` and
  `check(fps)`.
- `plant(profile, frames, *, base, spot, clamp, balance, margin_m)` is the same pass on any `DanceFrame` sequence a
  style already has, and `ground(profile, pose, feet)` lays one pose's feet flat. Style adapters call these; the
  stick adapter is to switch to them.
- `seated(profile)` is a base pose on a seat at knee height, feet flat on the floor.
- `stance(profile, *, width, bend, turnout, clamp)` is a standing base pose with the feet flat and `width` hip heights
  apart, turned out by `turnout` radians, and the hips sunk until the knees bend by `bend` radians (`knee_bend(profile,
  pose)` reads it); the defaults are `STANCE_WIDTH` 0.5, `STANCE_BEND` 0.55 and `STANCE_TURNOUT` 0.25.
- `Performance.dance_frames(fps)` gives the solved floor pass back as ordinary `DanceFrame`s on the unspotted base.

**Planted feet.** A planted foot lands where the free pose puts it at the first moment of its plant, laid flat on the
floor and turned the way it points; from then its ball stays on that spot. When the body turns on the floor a planted
foot pivots on its ball by the same turn, as a dancer's does. The leg is solved onto it by `retarget`'s leg solve,
which now takes the foot's world turn (`reach(..., turn=)`). Over `BLEND_S` either side of a plant the foot eases on
and off the spot. A free foot is kept above the floor. When the far foot of a wide stance is out of the leg's reach,
the hips sink (at most 0.3 hip heights) until it is in reach at 99.5 % of the leg's length, as a dancer bends the
standing knee; the foot is never dragged.

**Balance.** The centre of mass weighs each segment by a person's mass shares (Winter, 4th ed., table 4.1) at the
middle of its bone. At each key of the dance (a phrase's keys, each move entry's start, each change of planted feet)
the least horizontal shift of the hips is solved, in eight passes and at most 0.5 hip heights, that puts the centre of
mass `margin + 0.25 × foot width` inside the support of the feet planted on both sides of the key; between keys the
shift moves on the later key's ease. So the weight is over the standing foot before the other lifts. `balance(fps)`
reports every frame whose centre of mass is less than `margin_m` (5 mm by default, less on a narrow foot) inside the
support of its planted feet as a `BalanceFinding`; `check` and `strict=True` refuse with `BalanceError`. A frame in the
air or on a seat is not checked. A leg past its joint limits is refused with `FloorLimitError` unless `clamp`.

**Support from `body`.** The support is `body`'s public geometry: `support_footprint` under each planted ankle,
turned the way the foot points, on the character's `sk.body_profile` (the joint table's sole, 0.068 and 0.044 of the
height for width and heel, scaled with the foot), `support_hull` of those corners, and `support_margin` for how far the
centre of mass stands inside. The centre of mass is this module's own: `body` offers a torso mass proxy, not a
segment-weighted centre.

**A bent-knee, wide stance.** A class dancer stands low on a wide base: the dance study ([ADR 0196](0196-dance-style-from-reference-video.md)) measured the knees
bent 26°–62° and the stance 3.1–7.2 head radii wide, where the rest pose stands straight and narrow. `stance` lays both
feet flat at `±width / 2` hip heights, then finds the hips' drop by bisection (40 halvings over at most 0.7 hip
heights) at which the leg solve bends the knees by `bend`. A drop the feet cannot follow (a wide base on straight legs)
is refused with `FloorError`; a leg past its joint limits with `FloorLimitError` unless `clamp`. Passed as `base=`, it
is the pose every phrase key adds its deltas onto, so a phrase's root drop sinks into bent knees, not into the floor.

**The floor pass as frames.** A measure that reads `DanceFrame`s (the study's `dance_style.check`, the swing layer)
sees the legs only as the keys set them: a root drop in raw frames moves the whole body down. `dance_frames(fps)`
re-expresses each solved pose as a frame on the unspotted base: the travel and turn as `floor`, the hips' solved
offset as `root` in head radii, every other control as a joint delta, and the feet the pass held as `planted`.
`dance_pose` turns each back into the solved pose within 1e-6 m, so the folded knees reach any reader of frames.

**Rejected: a second leg solve inside `dance_pose`.** `dance_pose` is a pure map from deltas to a pose that every
style shares; solving legs there would plant feet twice for a style that already calls `plant`, and would give a
different body to a reader that never asked for a floor.

**Ensemble.** `ensemble(source, dancers, groove, *, seed, variation)` gives each `Dancer(profile, spot, delay_beats,
base)` its own performance from its `Spot(x, z, facing)`. A `random.Random(seed)` draws, dancer by dancer, a timing
shift of up to 0.04 beats and a size of the moves within 6 %, both times `variation`; the same seed gives the same
ensemble. `formation("line" | "wedge", count, spacing_m)` places up to 16 dancers.

### The class phrases

Four original one-eight phrases ship in `assets/dance/phrases.json`, made for a hip-hop class at 122.65 BPM and copied
from no routine: `groove-step` (a step-touch with a bounce on every count, travelling right and back, forearms
punching), `kick-ball-change` (two bounces, a kick-ball-change on each side), `plie-roll` (step wide, a plié with the
arms overhead, two body rolls rising, step in) and `turn-travel` (a step-pivot quarter turn to the left, travel, a
pivot back to the front). Every step lands on both feet, moves the weight on the next sixteenth and lifts on the one
after, so the balance shift always has a key to move on.

Every key also carries the class groove on a two-beat cycle, `c = cos(π × beat)`, from the study's measures: the legs
open by 0.1 radian a side, the hips sink 0.09 hip heights and bounce 0.06 down on the odd counts, and a single-foot key
rises 0.1; the chest and upper chest twist by 0.2 radian and tilt by 0.05 (shared 0.6 and 0.4), the neck sways by
0.04, the head nods by 0.05 and the chest leans 0.05 into the down count. `kick-ball-change` and `turn-travel` take
half the hips' motion and `turn-travel` no extra width, so the kick and the pivots stay inside the ankles' limits;
`plie-roll` keeps its own depth and width. The groove step's lifts on every "and" raise the hips once a beat: without
them the bounce is half time, but the cartoon's standing foot rolls past its limit.

Each key keeps its own timing: a `hit` holds the last pose for 65 % of the span and strikes in the last
`HIT_SHARE` (35 %) at about three times a `smooth`'s peak speed; a `smooth` leaves and lands at rest with its peak
speed at the middle. These are the timing waveforms this ADR ships; a per-key attack, release and peak-speed time
belongs to the timing work's `curve` waveform in the moves schema, which a key is to name once it lands.

### Review

`tools/dance_views.py --phrases` dances phrases in order on a fixed floor whose grid stays put while the body travels
over it, with a `three-quarter` view beside `front`, `left` and `top`, planted feet marked, and `--ensemble` puts every
character in one row in a formation with a `--canon`. A character is a preset or a profile record's path, and
`@seated` dances from `seated(profile)`.

## Consequences

- Every shipped phrase is tested on every preset at 50 pictures a second: no limit passed, planted balls and ankles
  within 2 mm, no frame off balance, no foot through the floor. The tests hold bounds, not a preset's lengths.
- A phrase samples into ordinary `DanceFrame`s, so anything that reads frames (a style adapter, a study that measures
  a dance) reads phrases too.
- The floor pass solves legs for every picture; a one-eight phrase takes a few seconds per character to perform and
  sample at 50 pictures a second.
- A test differentiates every shipped transition, joint and floor channel alike: a hit holds and strikes late at
  high speed, a smooth speeds up then slows down about its middle. Landing poses alone do not pass it.
- `dance_style.check` against the study's `studio-hiphop` record is the measure for the class phrases, read through
  `dance_frames` so the folded legs count. The phrases come closer to the class without matching it: the hips ride
  higher than the class's, the step-based phrases travel further a beat, and the narrow-hipped cartoon's foot roll
  limits how wide and how much the upper body sways.
- `plant` over a phrase's raw frames does not know which foot stepped, so the floor's travel drags the standing leg;
  `plie-roll` sampled raw and planted passes the ankle's flex limit by up to 0.03 radian. Phrases go through
  `perform`.
- The balance shift is horizontal only and a jump is not checked in the air. A phrase that needs the weight moved
  faster than a sixteenth, or leaves the body over one foot without a key to move on, is reported, not fixed.
