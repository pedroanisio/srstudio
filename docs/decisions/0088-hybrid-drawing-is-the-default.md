---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0088: The hybrid drawing method is the default for new work

- Status: accepted (2026-11-01), on the operator's word
- Back to the [library README](../../README.md)

## Decision

The hybrid, layered method of [DRAWING.md](../../DRAWING.md) is where new work starts. Anything rigid seen from more
than one angle is modelled and drawn from a 3D proxy, people stay on their rigs, the far plane is drawn, and
information stays vector.

Default means the method new work starts from, not a switch in the code. No style's builder changed, and a style whose
look is flat keeps it, as the table in DRAWING.md says. Published reels stay frozen (ADR 0040), an approved drawing stays
pinned (ADR 0047), and a new look still goes to the operator as a rendered, animated clip.

The rigid-object layer moved out of a study into the library:

- `srstudio.proxy` turns meshes into cel plates: a light pass and a flat part-id pass at 2× oversample, tone bands per
  part, and ink where part families meet. `layers` cuts them into back, front and under, so people draw between the
  first two and wheels ride under both. `View` projects a scene point to the frame, and `Recipe` holds a style's
  conversion.
- `srstudio.vehicle` adds a tyre to a model and a drawn rim that turns on the disc `View.disc` gives. A rim stays a
  vector drawing, so a turning wheel costs no plates.
- `srstudio.on_beat` puts `ride`, `sway` and `alternate` on a `music.Groove`.
- `music.measure` and `srstudio beat` read that groove from a recorded track.
- `clay.Model` gained `loft`, `strut` and `revolve`.

`forms`, `paint` and the typed scene records of DRAWING.md are still unbuilt.

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
  frames differed by at most one 8-bit level.

`music.measure` read the study's reference track at 129.0 BPM with a bar opening at 1.539 s, matching the 129 BPM and
1.535 s measured by hand. On its first ten seconds alone it read 128.8 BPM with the bar one beat early, at 1.066 s, so
the bars need more of the track than the tempo does. Measure the whole track when the bars matter.

The acceptance gates in DRAWING.md for a moving camera, palette, temporal stability, continuity and render budget have
not been measured. The operator made this the default ahead of them; they remain the gates for each proof.

## Alternatives

- **A `method=` switch on `Style`:** would suggest every style routes through one renderer. A Collage reel stays paper
  and a Maps reel stays a map, so each episode takes the layers its look needs.
- **The engine's posterize, gradient map and outline effects:** cheap, but they cannot tell one part from another or
  draw an interior line. The part-id pass does both.
- **Rims as plates:** a rim's turn would need a new plate per angle. A vector rim over a tyre plate costs none.
- **Tempo from the beat's fold alone:** read a 3-3-2 rhythm at two thirds of its tempo, 86 BPM on a 129 BPM track.
  `measure` now asks the beat, its double and the bar to repeat together.
