---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0091: The hybrid drawing method is the default for new work

- Status: accepted (2026-11-01), on the operator's word
- Back to the [library README](../../README.md)
- Corrected by [ADR 0256](0256-characters-and-location-looks-are-chosen-per-episode.md): "people stay on their rigs"
  described the drawn styles taking the rigid-object layer and is no general rule; how a character is made is chosen
  per episode or style

## Decision

The hybrid, layered method of [DRAWING.md](../../DRAWING.md) is where new work starts. Anything rigid seen from more
than one angle is modelled and drawn from a 3D proxy, people stay on their rigs, the far plane is drawn, and
information stays vector.

Default means the method new work starts from, not a switch in the code. No style's builder changed, and a style whose
look is flat keeps it, as the table in DRAWING.md says. Published reels stay frozen (ADR 0040), an approved drawing
stays pinned (ADR 0047), and a new look still goes to the operator as a rendered, animated clip.

The rigid-object layer moved out of a study into the library:

- `srstudio.proxy` turns meshes into cel plates: a light pass and a flat part-id pass at 2× oversample, tone bands per
  part, and ink where part families meet. `layers` cuts them into back, front and under, so people draw between the
  first two and wheels ride under both. `View` projects a scene point to the frame, and `Recipe` holds a style's
  conversion.
- `srstudio.vehicle` adds a tyre to a model and a drawn rim that turns on the disc `View.disc` gives. A rim stays a
  vector drawing, so a turning wheel costs no plates.
- `srstudio.on_beat` puts `ride`, `sway` and `alternate` on a `music.Groove`.
- `music.measure`, `music.reading` and `srstudio beat` read that groove from a recorded track.
- `clay.Model` gained `loft`, `strut` and `revolve`.

`forms`, `paint` and the typed scene records of DRAWING.md are still unbuilt.

`examples/car_vibe` is the worked example, built by its test on every run. It redraws another creator's cartoon, so it
stays in `examples/`, declares no post and is never a release.

`scipy` is now a declared dependency. It replaces the Euclidean distance transform, binary morphology, hole filling,
Gaussian filter and zoom that `proxy` would otherwise have to write and maintain.

## Verification

Each of these ran against engine 0.8.0:

- Landmarks on proxy plates land within 1 px of `View.project`, at the part-id pass, from one still view.
- A drawn rim lands within 5 px of the projected disc on a rim 350 px tall. The rim is a straight skew and the lens is
  a perspective, so this tolerance is the approximation's own.
- A warm rebuild of `layers` runs the engine zero times and returns the same bytes.
- A study written before the library had this code was moved onto it. Its nine plates came out byte-identical, its
  scene differed only by key times moved at most 0.5 ms and a default attribute no longer written, and three sampled
  frames differed by at most one 8-bit level. That proof holds up to a later fix: `View.stretch` used to leave normals
  as they were, so the light landed on the unstretched model. With normals corrected, up to 0.27 % of a plate's pixels
  move by more than 8 levels, and the three sampled frames still read the same by eye.
- Rendering the study's frames twice, out of order and in separate processes, gave byte-identical frames.

`read_parts` reads a part under 3 px wide in the part pass, 1.5 px on the final frame at 2× oversample, as what surrounds
it. A pixel blended half and half between two parts lands exactly on a third part's colour for 224 of the 2,016 pairs of
the palette, so width is what tells the two apart. A thinner part needs a higher `oversample`.

`music.reading` was checked on two sets of tracks of known grid. The study's reference track was hand-measured at
129 BPM with a bar opening at 1.535 s. It read 129.0 BPM and 1.539 s whole, and within 5 ms of that bar line on its
first 8, 10, 14, 20 and 30 seconds. Of eleven tracks from `music.render`, 84 to 164 BPM in steps of 8, nine read the
right tempo and bar line, whole and on eight bars. The 84 BPM track read at double, 168, with its bar line right; the
164 BPM track read at half, 82, with its bar line 0.17 s off. The lean toward 120 BPM cannot separate those two pairs.
A reading of six seconds, 3.2 bars, placed the reference's bar a beat off. Under eight bars a reading says it is unsure.

Click tracks from 60 to 195 BPM in steps of 5, three start times and two lengths, gave 168 readings. Every one from 75
to 165 BPM read the right tempo and bar line, 114 in all. The other 54 read at the octave: 60 to 70 BPM at double and
170 to 195 BPM at half. An even pulse holds nothing that tells them apart, so `reading` does not flag it. It takes
`near`, `srstudio beat --near`, the tempo to lean toward: given its own tempo, each of those 54 read the right tempo
and bar line.

The acceptance gates in DRAWING.md for a moving camera, palette, continuity and render budget, and the part of temporal
stability that needs a moving light or texture, have not been measured. The operator made this the default ahead of
them; they remain the gates for each proof.

## Alternatives

- **A `method=` switch on `Style`:** would suggest every style routes through one renderer. A Collage reel stays paper
  and a Maps reel stays a map, so each episode takes the layers its look needs.
- **The engine's posterize, gradient map and outline effects:** cheap, but they cannot tell one part from another or
  draw an interior line. The part-id pass does both.
- **Rims as plates:** a rim's turn would need a new plate per angle. A vector rim over a tyre plate costs none.
- **Tempo from the beat's fold alone:** read a 3-3-2 rhythm at two thirds of its tempo, 86 BPM on a 129 BPM track.
  `measure` now asks the beat, its double and the bar to repeat together.
- **The bar line from the low end alone:** a kick on one and three makes those beats a tie, and it put a 110 BPM song's
  bar two beats off. The low end now picks the strong marks and the turn between whole bars picks among them. A sum of
  the two, or their product, read fewer tracks right.
