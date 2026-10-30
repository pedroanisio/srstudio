---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0043: Lit Toon rooms, with the light drawn under the desk

- Status: accepted; implemented 2026-10-30 (`srstudio.toon_rooms`, `toon_sketch.Staging.lit`,
  `toon_sketch.Shot.light`; `tests/test_toon_rooms.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The Toon sets have light, but only as paint. A glow in `toon_sets.home` is a radial gradient that never changes.
`toon_sets.desk_lamp` can switch its cone on and off, but the light falls on nothing else. Two premises need light
that a sketch can drive:

- a living room at night, lit by a lamp and the TV, for everyday tech: streaming, the smart home, a password at
  1 a.m.;
- a service counter or waiting area under fluorescent tubes: a bank, a clinic, a government office.

The lights need states that change over time: on, off, flicker, dimming, and a screen glow that changes colour.
The light has to fall on the character's side of the frame, not only on its source.

There is a constraint. The signature (ADR 0001) sits on `toon.desk`, which is drawn in front of every Toon shot.
It has to stay readable in every light state. Its code mark is already a low-contrast mark: `DESK_CODE` #8f4237
on `DESK_FRONT` #b25647 is 1.44:1 by the WCAG luminance formula. Any shade over it lowers that ratio further.

## Decision

1. **A new module, `toon_rooms`, with two rooms.**
   - `toon-lounge`: a floor lamp (`lamp`) and a wall TV (`tv`).
   - `toon-counter`: two fluorescent fixtures (`tubes`) and a NOW SERVING board (`board`), which also takes
     `serving=` tickets.

   `ROOMS` maps each name to its main light, its screen, the default cues and the boxes of its objects. A sketch
   selects a room by name with `stage` or `dress`. An unknown room, light or option is refused with
   `ToonDataError`.

2. **The light model is a level from 0 to 1, keyed on the composition clock.** `level_keys` turns cues into keys:
   - `on` holds 1 and `off` holds 0;
   - `dim` fades linearly from the level before it to `DIM` (0.35) over `FADE` (1.5 s). The fade uses the key's
     own `interpolation="linear"`; every other key holds;
   - `flicker` repeats the `FLICKER` pattern with `cycle_keys` until the next cue.

   `parse_lights` refuses the following:
   - a cue list that does not start at 0;
   - times out of order, or times that are not finite numbers;
   - a cue at or after the end;
   - an unknown state;
   - a colour on a light that is not a screen;
   - an unknown colour;
   - a screen whose first cue has no colour;
   - a cue that comes before a dim has finished. This keeps every key time distinct.

   A still (`end` 0) rests at its first cue's level and has no animation.

3. **Each screen colour is its own layer, shown only while that colour is on.** It is drawn once per colour used
   and gated on the colour's spans, inside a group keyed to the screen's level.

4. **The light falls in two places.**
   - The sources follow their level in the set (`shot.back`): the lamp's shade and glow, the tube diffusers and
     their glow, the TV picture and its halo, the board's face and its ticket.
   - The rest goes in a light layer. It holds a full-frame shade in a `blend="multiply"` group, with opacity
     `SHADE_MAX × (1 − main level)` (`SHADE_MAX` 0.6). It also holds one `blend="screen"` glow group per light: a
     wide radial glow over the character's side of the frame, with opacity proportional to that light's level.

5. **The light layer goes between the character and the desk.** `Staging.lit` (default `False`) makes the build
   add one group per shot, after the character drawer and before `staging.desk`. The build passes it to the dress
   as `Shot.light` (default `None`). The desk, which carries both signature marks, is drawn after the light, so its
   colours do not change in any state. With `lit` left at `False` the build makes no extra group and allocates no
   extra id. Existing sketches build byte for byte as before.

6. **Signature readability is tested on the engine.** For each room, a cropped scene is rendered in each state:
   on, off, dim, and flicker at its lowest. The test compares the signature's pixels with the light-on frame. A
   signature pixel is any pixel that differs from an unsigned render.
   - None of the code's pixels on the desk front may change.
   - At least 95 % of all signature pixels must be unchanged, with a mean change of at most 4 levels in 255. The
     cactus's flower and its anti-aliased edges stand against the room, so a few edge pixels see the shade.
   - A control renders the same light drawn over the desk. That arrangement must fail the check, so the check can
     fail.

   A second test renders the character's chest and checks two things. The chest darkens as the main light goes off
   or dims. The chest also takes the screen's colour: the blue glow raises the blue channel and the red glow raises
   the red one.

   The tests read the PNGs with a small pure-Python reader (`tests/support/png.py`), so the test dependencies do
   not change.

## Rejected alternatives

- **Painted-on light**: a fixed lit look per room. It cannot be driven over time, which is the requirement.
- **One shade over the whole shot, the desk included, kept above a contrast floor.** Any shade lowers the code's
  1.44:1, so the floor would have to be the unlit ratio, which means no shade at all.
- **A shade with a hole cut round the signature.** The lit patch around the cactus reads as a spotlight, and it
  draws the eye to the mark the style keeps quiet.
- **Engine effects such as a vignette or glow on the shot group.** An effect isolates the group into an offscreen
  buffer, which would include the desk. ADR 0030 also records the cost of GPU effects. The rooms only need group
  blends and gradients.
- **Animating gradient-stop colours for the screen.** Not verified on this engine. The gated per-colour layers were
  verified by render, and the gates are ordinary hold keys.
- **Adding the rooms to `toon_sets.py`.** That module was being changed in parallel. A separate module keeps the
  shared-file edits to the build's two fields and one line.
- **Drawing the light from a custom `staging.desk`.** The desk callable gets only the canvas and the shot group.
  It does not know the sketch's end, the appearance or the cues, so it cannot key the light.

## Consequences

- A lit sketch sets `Staging(lit=True)` and calls `toon_rooms.dress(shot, name, lights)`. Dressing a shot that is
  not lit is refused, so the light is never drawn over the desk by mistake.
- No episode uses the rooms yet. The catalog gallery's coverage check counts only parts that rendered episodes
  use, so the rooms need no gallery note until an episode uses them.
