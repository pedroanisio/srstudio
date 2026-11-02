---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# Dance moves on the beat

Back to the [authoring reference](authoring-reference.md).

`srstudio.dance` holds dance moves as data on canonical joint names and times them on a `music.Groove`, so any character
can dance to any song. It returns deltas: a skeleton turns them into a pose, and a body keeps planted feet planted. The
decision and the schemas are in [ADR 0186](decisions/0186-dance-moves-on-the-beat.md).

## Sample a preset

<!-- dance-recipe:start -->
```python
from srstudio import dance
from srstudio.music import Groove

groove = Groove(129)
move = dance.moves()["seat-groove"]

frame = dance.sample(move, groove, 1.0)
print(frame.root, frame.support)  # right, up, forward in head radii; "seat"

bob = [f.value("root.up") for f in dance.frames(move, groove, 0.0, 32 * groove.beat, 25)]
reading = dance.measure_dance(bob, 25, groove)
assert dance.SEAT_GROOVE_BOB.misses(reading) == ()
```
<!-- dance-recipe:end -->

The presets are `seat-groove`, `bob`, `sway`, `bounce`, `shoulder-shimmy`, `head-nod`, `arm-pump`, `arm-wave-overhead`
and `step-touch`, and the arm gestures below. A frame's `value(target)` reads any canonical target and returns zero for one the dance does not move.
`planted` names the feet a body should hold still, `support` says how the body is held up, and `expression` is the face
held for the phrase. Only `seat-groove` is measured against a reference, and the presets have not been judged on a drawn
body.

## Dance on a character

```python
from srstudio import dance, skeleton
from srstudio.dance_pose import dance_pose
from srstudio.music import Groove

groove = Groove(129)
character = skeleton.preset("cartoon")
frame = dance.sample(dance.moves()["arm-wave-overhead"], groove, 0.3)

danced = dance_pose(character, frame, clamp=True)
print(danced.dropped)  # canonical fingers this character's hands do not have
joints = skeleton.world(character, danced.pose)  # every joint's frame, ready for a style to draw
```

`dance_pose` turns the root's head radii into metres of this character's head, so a big head bobs more, and adds the
joint deltas onto `base` (the rest pose unless a style passes its own). A joint the character lacks is dropped and named,
never applied elsewhere. See [the skeleton guide](authoring-skeleton.md) for profiles and drawing.

## Review a dance in three views

```sh
python tools/dance_views.py generated/character-proofs/<name>/views.mp4 --moves bob,arm-pump --bars-each 2
```

Every dance gets a three-plane review before its look is judged: one row per character preset and one column per
orthographic view, `front` (x, y), `left` (z, y, seen from the character's left side, facing screen right) and `top`
(x, z, front down the screen, a tick on the head where it faces), on a track `music.render` synthesises at the same
tempo. It draws bones only, so it shows what the skeleton does with a move before any style draws it. Leave out
`--moves` for every preset.

## Dance arm gestures

`clap`, `point-up`, `raise-the-roof`, `hand-wave-side`, `shoulder-roll` and `hip-sway` are full-arm gestures on the beat,
and `hands-up` is a pose to hold ([ADR 0192](decisions/0192-dance-arm-gestures.md)). Each is tested on the skeleton's
forward kinematics on the `realistic`, `cartoon` and `stick` presets, and dances on all three within limits without
clamping. A move that never moves gives its pose to an entry's `hold` with `held()`:

<!-- dance-gestures:start -->
```python
from srstudio import dance
from srstudio.music import Groove

presets = dance.moves()
routine = dance.Routine(
    8,
    (
        dance.Entry(0, 4, presets["clap"], expression="grin"),
        dance.Entry(4, 8, presets["seat-groove"], transition_beats=2, hold=presets["hands-up"].held()),
    ),
)
frame = dance.sample(routine, Groove(120), 9.0)
assert frame.value("left_upper_arm.down_up") == presets["hands-up"].held()[0][1]
```
<!-- dance-gestures:end -->

The cartoon's arms are short against its head and shoulders: its pointing and raised hands reach the middle of its head,
not above it, and its clap meets at `intensity=2.0`. A raised arm rides the body with no lag, as in the reference reel.
`hold` adds to the move, so hold `hands-up` over a move that leaves the arms alone (`seat-groove`, `head-nod`,
`shoulder-roll`, `bob`, `sway`).

## Write a move

A pattern hits `+amplitude` once a cycle, `phase` beats after the grid's beat. Amplitude is half of peak to peak, its
sign picks the direction of the hit, and it is in radians on a joint or head radii on the root. `snap` is the fraction
of the cycle spent striking onto the hit.

```json
{
  "schema": "srstudio.dance-moves/1.1.0",
  "moves": [
    {
      "name": "chest-pop",
      "description": "The chest pops forward on two and four; the neck gives after it and settles.",
      "support": "either",
      "loop_beats": 2,
      "lags": {"head": 0.1},
      "patterns": [
        {"target": "chest.front_back", "waveform": "sine", "cycles": 0.5, "per": "beat",
         "phase": 1, "amplitude": -0.12, "snap": 0.25},
        {"target": "head.nod_down_up", "waveform": "sine", "cycles": 0.5, "per": "beat",
         "phase": 1, "amplitude": -0.05, "snap": 0.25}
      ],
      "follow": [
        {"target": "neck.nod_down_up", "source": "chest.front_back", "gain": 0.4,
         "lag": 0.05, "frequency": 3, "damping": 0.5}
      ]
    }
  ]
}
```

A `follow` entry (moves 1.1, [ADR 0201](decisions/0201-dance-swing.md)) makes a joint ride a pattern's target late:
`gain` times the source, in the follower's units per the source's, read `lag` beats late through a damped spring of
`frequency` cycles per beat and `damping`. Under a damping of 1 the follower overshoots and settles, the follow-through
that keeps a move from looking dry; `damping * frequency` is at least 0.3, so a spring settles within two beats. A
follower moves only a joint no pattern moves, and follows a pattern, never another follower.

`support` is `seat`, `feet` or `either`. A `feet` move declares `contacts` so that a foot is planted at every moment of
its loop. `parse_moves` and `load_moves` refuse anything outside the schema; the [ADR](decisions/0186-dance-moves-on-the-beat.md)
lists the fields.

## Choreograph a song

Measure the track, then place moves on its bars:

<!-- dance-routine:start -->
```python
from srstudio import dance

text = """{
  "schema": "srstudio.dance-routine/1.0.0",
  "track_bars": 24,
  "entries": [
    {"bars": [0, 8], "move": "head-nod", "expression": "eyes-closed"},
    {"bars": [8, 16], "move": "seat-groove", "transition_beats": 2, "expression": "grin",
     "hold": {"head.turn_left_right": 0.3}},
    {"bars": [16, 24], "move": "seat-groove", "intensity": 0.6, "mirror": true, "transition_beats": 2}
  ]
}"""
routine = dance.parse_routine(text, dance.moves())
```
<!-- dance-routine:end -->

`dance.song_map(path, groove)` gives `beat_db`, `phrase_db` and `parts`; `boundaries` are the bars a new level opens on.
It reports louder and quieter parts, never which one is the chorus. Read the grid first with `music.reading(path)` or
`srstudio beat`.

## Choreograph by level

`srstudio.choreograph` places the moves for you ([ADR 0193](decisions/0193-routine-from-a-song.md)): one move a phrase,
small moves on quiet parts and arm gestures on loud ones, only moves the character's `support` allows, at most
`max_repeat` phrases of one move in a row with every second one mirrored, and one face held a phrase. The same `seed`
and song give the same routine.

<!-- dance-choreograph:start -->
```python
from srstudio import choreograph, dance
from srstudio.music import Groove

groove = Groove(120)
song = dance.SongMap(
    groove,
    4,
    (0.0,) * 64,
    (-6.0, 0.0, 0.0, -6.0),
    (dance.SongPart(0, 4, -6.0, "low"), dance.SongPart(4, 12, 0.0, "high"), dance.SongPart(12, 16, -6.0, "low")),
)
routine = choreograph.choreograph(song, support="seat", seed=7)
assert [(e.start_bar, e.end_bar) for e in routine.entries] == [(0, 4), (4, 8), (8, 12), (12, 16)]
assert routine.entries[1].move.name in choreograph.HIGH_MOVES
assert dance.parse_routine(dance.dump_routine(routine), dance.moves()) == routine
```
<!-- dance-choreograph:end -->

On a recorded track, `choreograph.choreograph_track(path, groove, support="feet", seed=7)` maps it first, and
`srstudio choreograph song.wav --support feet --seed 7 > routine.json` reads the grid as `srstudio beat` does and
prints the routine. Pass a `choreograph.Palette` to draw from other moves or faces, and `library=` when it names moves
outside the presets. A routine for a cartoon clap still needs `intensity=2.0` set on that entry by hand.

## Check a groove

`measure_dance(series, fps, groove)` reads `cycles_per_beat`, `rise`, `fall`, `snap_ratio`, `peak_to_peak`, the `hit`
against the beat, and `resolution`. Build a `DanceTarget` for a dance you have measured, and treat `misses(reading)` as
the test. Give it several bars: an estimate on two cycles moves with every sample. At 25 pictures a second a stroke
reads to about one picture when the channel carries noise of five percent of its size.

## Check a swing

A groove can land on every beat and still look dry: a head that travels in straight strokes, eases each one evenly and
stops dead. `dance_pose.body_series` reads what a dance shows on a character facing the camera, frame by frame: the
head's centre across and up in head radii, its roll and the neck's lean. `measure_swing` reads the head's `path` (its
`shape`, `openness`, the `lead` of the sideways motion over the vertical and their `ratio`), the neck's `lean`, the head's
`lag` after it, its sideways `rebound` and its `roll`. `SEAT_GROOVE_SWING` holds the seat-groove to the car reel it was
measured from:

<!-- dance-swing:start -->
```python
from srstudio import dance
from srstudio import skeleton as sk
from srstudio.dance_pose import body_series
from srstudio.music import Groove

groove = Groove(129)
move = dance.moves()["seat-groove"]
lean = move.follows[0]
print(lean.target, lean.source, lean.gain, lean.lag)  # neck.tilt_left_right root.right 2.3 0.32

body = body_series(sk.preset("cartoon"), dance.frames(move, groove, 0.0, 16 * groove.beat, 50))
reading = dance.measure_swing(body.across, body.up, body.roll, body.lean, 50, groove)
assert dance.SEAT_GROOVE_SWING.misses(reading) == ()
assert reading.path.shape == "loop" and reading.rebound > 0.01  # an open curve, and a stroke that follows through
```
<!-- dance-swing:end -->

`body_series` refuses a pose past a joint's limit, so it also checks that the swing fits the character. The seat-groove
reads the same on the realistic, cartoon and stick skeletons: its hips' slide is in head radii and its neck is half a
head radius on all three. Its head runs ahead of its neck's lean, where the reel's head follows the neck; the ADR names
why.

## Learn a style from a reference video

The dance study ([ADR 0196](decisions/0196-dance-style-from-reference-video.md)) measures how a real dancer moves and
holds our dances to it. It copies no routine: only style statistics on the beat grid reach the repository, as a
`srstudio.dance-style/1.0.0` record of ranges. The footage, its frames and its per-frame landmarks stay under the
workspace's `generated/` (`$WS/generated`, `$WS` the workspace that holds this checkout) on the machine that made
them.

1. Build the pose estimator's own interpreter once. It stays outside srstudio's dependencies:

   ```sh
   uv venv --python 3.12 $WS/generated/venvs/pose && chmod 700 $WS/generated/venvs/pose
   uv pip install --python $WS/generated/venvs/pose/bin/python mediapipe==1.2.0
   $WS/generated/venvs/pose/bin/python -I tools/pose_extract.py --fetch-models
   ```

   `--fetch-models` downloads the Pose Landmarker models (Apache-2.0) next to that interpreter and refuses a file
   whose digest is not the one pinned in the tool.

2. Extract the dancer: `$WS/generated/venvs/pose/bin/python -I tools/pose_extract.py VIDEO --out
   $WS/generated/dance-study/NAME/pose-track.json` follows the most central large person, or `--pick 0.4,0.5` the one
   nearest that point. A frame where the dancer cannot be told from a neighbour is written as lost, never guessed.
3. Measure and check, in srstudio's own interpreter: `python tools/dance_study.py measure TRACK --audio VIDEO --name
   NAME --description TEXT --out src/srstudio/assets/dance/styles/NAME.json`, then `python tools/dance_study.py check
   STYLE --audio VIDEO --out $WS/generated/dance-study/NAME/findings.json` dances every standing preset and a choreographed
   routine on the reference's grid and ranks what they miss. `page` writes the operator's local proof page.

The same check runs on any `DanceFrame` sequence. Here a synthetic record stands in for the estimator's:

<!-- dance-study:start -->
```python
from srstudio import dance, dance_style, pose_track
from srstudio import dance_study as ds
from srstudio.music import Groove

groove = Groove(120)
bounce = list(dance.frames(dance.moves()["bounce"], groove, 0.0, 4 * groove.bar, 15))
track = pose_track.from_data(ds.pose_record(bounce, 15))  # what an estimator facing the dancer would write
body = ds.reference_body(track)  # hips-relative, in head radii; refused frames are counted, never filled
assert body.used == len(bounce) and sum(body.rejected.values()) == 0
reference = dance_style.Reference(
    "a synthetic bounce", track.source.sha256, track.estimator.name, track.estimator.version,
    track.estimator.model_sha256, 8.0, len(bounce), body.used, dict(body.rejected), 120.0, 4, 0.0,
)  # fmt: skip
style = dance_style.derive(
    ds.measure_style(body, groove), name="bounce-study", description="our bounce, measured back",
    reference=reference, generated_by={"tool": "authoring-dance.md", "model": "none"},
)  # fmt: skip
assert dance_style.check(style, bounce, groove, 15).misses == ()
arms = dance_style.check(style, list(dance.frames(dance.moves()["arm-pump"], groove, 0.0, 4 * groove.bar, 15)), groove, 15)
assert arms.misses and arms.misses[0].severity >= arms.misses[-1].severity
```
<!-- dance-study:end -->

Each miss names the channel, the measure, our value, the reference's range and the trust of the channel; the score is
their summed severity. Read `torso.lean` and `torso.roll` lightly: a single camera reads depth poorly. A reference
measures no travel across the floor: its camera follows the dancer and its estimator's metres start at the hips.
