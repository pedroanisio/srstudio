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
and `step-touch`. A frame's `value(target)` reads any canonical target and returns zero for one the dance does not move.
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

## Write a move

A pattern hits `+amplitude` once a cycle, `phase` beats after the grid's beat. Amplitude is half of peak to peak, its
sign picks the direction of the hit, and it is in radians on a joint or head radii on the root. `snap` is the fraction
of the cycle spent striking onto the hit.

```json
{
  "schema": "srstudio.dance-moves/1.0.0",
  "moves": [
    {
      "name": "chest-pop",
      "description": "The chest pops forward on two and four.",
      "support": "either",
      "loop_beats": 2,
      "lags": {"head": 0.1},
      "patterns": [
        {"target": "chest.front_back", "waveform": "sine", "cycles": 0.5, "per": "beat",
         "phase": 1, "amplitude": -0.12, "snap": 0.25},
        {"target": "head.nod_down_up", "waveform": "sine", "cycles": 0.5, "per": "beat",
         "phase": 1, "amplitude": -0.05, "snap": 0.25}
      ]
    }
  ]
}
```

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

## Check a groove

`measure_dance(series, fps, groove)` reads `cycles_per_beat`, `rise`, `fall`, `snap_ratio`, `peak_to_peak`, the `hit`
against the beat, and `resolution`. Build a `DanceTarget` for a dance you have measured, and treat `misses(reading)` as
the test. Give it several bars: an estimate on two cycles moves with every sample. At 25 pictures a second a stroke
reads to about one picture when the channel carries noise of five percent of its size.
