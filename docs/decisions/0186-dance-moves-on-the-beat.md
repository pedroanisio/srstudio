---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0186: Dance moves are data on canonical joints, timed by the beat grid

- Status: proposed (2026-11-02)
- Back to the [library README](../../README.md)

## Context

Any srstudio character should be able to swing and dance to any song. The reel that set the bar is a seated car dance:
everything cycles once per beat, the body drops on the beat, a sideways snap lands with the drop, and faces and head
turns change only every few bars. Reading that reel frame by frame gave numbers, so a move can be held to them.

Dancing has to outlive any one drawing style, and it must follow a song's tempo rather than a fixed clip length.
`music.Groove` already owns the grid. The shared skeleton on the 55 joint names of srlocations' mannequin is being built
in parallel, so this layer addresses those names and imports nothing of it.

## Decision

`srstudio.dance` holds moves as data. A pattern is a function of beat position, so one move plays at any tempo. The
module knows no drawing style and no skeleton: its output is deltas on canonical names, and turning them into a pose,
and keeping planted feet planted, is the skeleton's and the body's job.

### Units

- A target is `"<joint>.<dof>"` in radians, or `root.right`, `root.up`, `root.forward` in head radii. The mannequin's
  hips translation is the root; `hips.right`, `hips.up` and `hips.forward` are refused as targets because their metres
  would not scale to a character.
- A dof named `a_b` reads negative toward `a` and positive toward `b`; a one-word dof (`stretch`, `close`, `stretched`,
  `spread`) reads positive toward that word. This reads the names, not the mannequin's code: the skeleton must confirm
  or convert it, and the presets' arms and legs depend on it.
- Time is in beats. A lag and a phase are beats, so they keep their musical meaning at any tempo.

### Move schema, `srstudio.dance-moves/1.0.0`

| Field | Holds |
|---|---|
| `schema` | the schema and version; another major is refused |
| `generated_by` | optional `tool` and `model` |
| `moves[]` | `name`, `support`, `patterns[]`; optional `description`, `loop_beats` (1), `lags`, `contacts` |
| `support` | `seat` (no leg patterns), `feet` (standing, with contacts) or `either` (no root or leg patterns) |
| `lags` | beats, 0..1, per chain: `root`, `torso`, `head`, `left_arm`, `right_arm`, `left_leg`, `right_leg` |
| `contacts[]` | `foot`, `from`, `to`: when a foot is meant to stay planted, in beats of the loop |
| `patterns[]` | `target`, `waveform`, `cycles`, `per`, `phase`, `amplitude`, `snap`; optional `swing` (0.5), `intensity` (1), `bias` (0) |

A pattern's value is `bias + intensity * amplitude * wave(u)`, where `u` runs from the hit: the channel reads
`+amplitude` at the hit and `-amplitude` at its far extreme, so amplitude is half of peak to peak and its sign says
which way the hit goes. `sine` is two half cosines, leaving the hit over `1 - snap` of the cycle and striking back in
`snap`; 0.27 is the reel's 1:2.6 sway. `hold` rests at each extreme and moves between them in strokes of `snap`.
`cycles` count per `beat` or per `bar`, and `swing` is where the off-beat eighth lands (2/3 is a triplet swing).

The model checks what the schema cannot say: a standing move has a foot planted at every moment of its loop, one foot
is not planted twice at once, a loop holds whole cycles of its per-beat patterns, and a seated move has no legs.

### Routine schema, `srstudio.dance-routine/1.0.0`

| Field | Holds |
|---|---|
| `track_bars`, `beats_per_bar` | the track; `beats_per_bar` defaults to 4 and must match the groove sampled on |
| `entries[]` | `bars` `[start, end)`, `move`; optional `intensity`, `mirror`, `transition_beats`, `expression`, `hold` |

Entries are in order and never overlap, a bar outside the track is refused, moves must exist, a transition fits in its
entry, and a routine never mixes `seat` and `feet` moves. Gaps are rest. An entry is a phrase: its `expression` is the
face held for it, and `hold` is a held pose, such as a head turn, because the reel changes those only at phrase level.

A transition crossfades move parameters from the entry that ends where this one starts, or from rest. A target both
moves place alike in time crossfades size, bias and snap. Other targets are weighted, because blending two periods
would make a chirp. Feet follow whichever move has passed halfway; the face switches when the entry opens.

Both documents are strict: one JSON object of at most 1 MB, no NaN or Infinity, no repeated key, no unknown or missing
field, no wrong type, no coercion, bounded lists. Malformed text raises `DanceDataError`, another schema
`DanceSchemaError`, and a value the model refuses `MoveError` or `RoutineError` at its JSON path.

### The measured target is the acceptance test

`measure_dance` reads a sampled channel back: cycles per beat, the rise and fall, peak to peak, and the hit against the
beat. Its reading of `seat-groove`, sampled at the reel's 25 pictures a second against 129 BPM, must meet two targets
in code, `SEAT_GROOVE_BOB` and `SEAT_GROOVE_SWAY`:

| Measured on the reel | Target |
|---|---|
| Everything cycles once per beat | 1 ± 0.02 cycles per beat, on both channels |
| Bob 0.26 to 0.50 head radius peak to peak | inside that range |
| Down in 0.19 s, up in 0.26 s | each ± 0.02 s |
| Sway snap about 0.12 s, return about 0.32 s | each ± 0.025 s, ratio 2.6 ± 0.3 |
| Sway about 0.2 head radius peak to peak | 0.17..0.23 |
| The drop lands on the beat, the snap with the drop | each within 0.02 s of the beat |
| The head does not rotate within a beat | no `head` or `neck` channel moves |
| A raised arm rides the body with no lag | no arm channel of its own, so no lag to have |

The reel's strokes sum to 0.45 s of a 0.465 s beat, so the sway's stroke tolerance is wider by that gap. Tests also
show that wrong moves miss: an even bob, half time, too big, off the beat. A cycle that is a whole number of pictures
lands every sample on the same few places, and a stroke cannot be read finer than that; the reading carries this as
`resolution`, and a target counts it as a miss rather than passing a stroke the samples cannot show.

The raised arm's tip moving 0.32 head radius against the head's 0.50 is not a test here. It is a position on a bone
chain, so it needs the skeleton's forward kinematics. Until then `seat-groove` carries the bob on the root, and an arm
riding it moves with the root in full.

### Song structure

`song_map` measures a track on a groove: energy on every beat, and phrases of `phrase_bars` merged into parts wherever
neighbouring phrases differ by `change_db` or more. A part is `high` or `low`, or `even` when the track has one level.
It reports level changes, not verse and chorus: which is the chorus is a reading of the song that energy cannot make,
and a routine only needs the bars where the level turns.

## Rejected alternatives

- **Per-frame baking only.** A baked curve fixes a tempo and a length, so a new song means a new bake, and it says
  nothing a test can read as a move. A pattern gives the same frames through `frames` and stays a move.
- **Style-specific dance code.** Each style would redraw the same timing, and the groove would drift between them. A
  style's rig reads canonical deltas instead.
- **Mocap only.** Capture holds one tempo and one performer, and a clip has to be retimed to a song, which breaks the
  snap the reel depends on. It brings data licensing too. A capture can still set a move's parameters, as this reel did.

## Consequences

- A move scales to any character and any tempo, and is tested against the dance it was measured from.
- The presets' dof signs assume the naming convention above. Until the skeleton lands, only `seat-groove`'s root
  channels are measured against a reference; the other presets are authored and have not been seen on a body.
- `seat-groove` carries the whole bob on the root because the head must not rotate within a beat and head position
  cannot be read without forward kinematics. A body that holds the hips on a seat decides how the root reaches the torso.
- A move that needs a held arm pose in a seated dance adds it as `hold`. `seat-groove` does not raise an arm itself.
