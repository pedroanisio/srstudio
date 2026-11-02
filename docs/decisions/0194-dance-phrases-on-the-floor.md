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
- The balance shift is horizontal only and a jump is not checked in the air. A phrase that needs the weight moved
  faster than a sixteenth, or leaves the body over one foot without a key to move on, is reported, not fixed.
