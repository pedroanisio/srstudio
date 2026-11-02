---
generated-by: Claude Sonnet 5.5 (claude-sonnet-5-5) in Claude Code
---

# ADR 0098: The wire car and the wire jet are props, with close-ups and anchors a person can sit at

- Status: proposed (2026-11-01), on the operator's request to reuse the two wireframe generators as library cars and
  jets for scenes
- Deciders: the operator; written by Claude Sonnet 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

Two scratch generators, a seeded car and a seeded fighter jet, drew 3D wireframes with their hidden lines removed. A
scene could not use them: they wrote their own pictures, not parts. The operator asked for them as parts, so that a
scene can have cars and jets, and then for a 30 s piece of Pedro driving the car and flying the jet.

## Decision

- `wire_view` owns the camera, the depth raster and the occlusion test both models share. `wire_car` and `wire_jet`
  supply the lines and the surface quads, seeded: the same seed gives the same vehicle, and a number reads as typed.
- `wire-car` and `wire-jet` are `prop` parts. Each ink is one stroked, unfilled path, so the scene behind shows through
  and a vehicle is ten shapes at most. Stroke widths scale with the width asked for.
- A close-up (`around`, `span`, `height`) sees the model at the frame's scale round a named anchor instead of fitting
  it to the picture. `driver-head` and `steering-wheel` are the car's anchors; `pilot-head` and, in a two-seater,
  `rear-pilot-head` are the jet's. `anchor(...)` returns where one falls on the canvas, with the pixels in a metre
  there, so a person can be seated at it at the scale of the car.
- `rows=(top, bottom)` keeps only the strokes between two heights, cutting a stroke where it crosses. A person goes
  between the two halves of one drawing: the upper half behind him, the lower in front.
- Every refusal is a typed error (`WireError`, `WireCarError`, `WireJetError`): an unknown anchor, a span or height that
  is not a number, a frame that shows no line, rows that are not a top above a bottom.
- `plate(light, ...)` of each prop is the second layer of a drawing in the sense of `DRAWING.md`: the model's own
  surfaces as a picture, to lie under its strokes. The depth raster that hides the lines also says which surface is
  nearest in each pixel and which material it is (`PAINT`, `TIRE`, `DARK`, `LEATHER`, `TRIM`); the normal is turned to
  face the lens and cut into four tones by its angle to `light` (the world direction towards the light, three finite
  numbers, not all 0). The tones of each material come from a `RAMPS` palette. A plate and the strokes of the same shot
  share one projection (it is cached once per seed, view, size and light), so they register to the pixel, and `rows`
  cuts the plate as it cuts the strokes. The character and the vehicle are lit from one light: the piece derives it
  from the sculpt's key light.
- Perspective: `distance` (metres from the model's middle; none is orthographic) puts the camera at that distance. The
  raster keeps a lens factor per pixel, nearer parts are larger, the hidden-line slack follows it, and an anchor reports
  the scale where it falls (`Anchor.scale`), so a person seated in a car is the size of the car there. A camera inside
  the model is a typed error. Orthographic output is unchanged when `distance` is left out.
- Wheels: `wheels` (`all`, `body`, `front`, `rear`) and `spin` (radians, positive = forward) draw the wheels apart
  from the body. A wheel layer is unoccluded by the body and goes beneath it; the body layer (`wheels="body"`) removes
  the wheel lines, paints the wheels as `HOLE` (the surface hides lines but writes no paint, so the layer beneath shows
  through) and keeps their silhouettes out of the ink (`quiet`). Every layer is framed by the whole car, so layers
  register. `hub-front` and `hub-rear` are anchors, and a car says how many `spokes` it has, so a piece can turn a
  wheel at the angles that repeat.
- Edge: `rows` takes a `tilt` (pixels of height per pixel across) that slopes its cuts, and `edge(anchor, below,
  reach)` of each prop measures the top of the paint under an anchor in the surfaces themselves, returning the `rows`
  and `tilt` that follow a door's top or a coaming as the camera sees it. A piece no longer guesses a belt line.
- Both parts are `proposed` in `parts.json` until the operator approves them from the rendered pictures.
- Meshes: `wire_mesh.car_model(seed)` and `jet_model(seed, model=)` give the same surfaces as real meshes for the
  engine's 3D pass: quads welded, normals smoothed across edges flatter than `CREASE` (38 degrees) and kept hard
  beyond it, faces wound outward whichever way the generator wound them, one mesh per jet part (the glass is left
  out), a tyre and a rim for each car wheel made about its hub so a wheel turns on its own pivot, and the same anchors
  (`driver-head`, `steering-wheel`, `pilot-head`). Units are scene units (100 = 1 m, y down, z away from the lens). A
  bad crease, a missing material, no quads, a corner that is not a number or a quad with no area is a typed
  `WireMeshError`. This is the road to a real scene: the pilot builds a street and a cloud sea around these meshes,
  shoots them with perspective cameras and paints the picture over with one shader (`episodes/pilots/pedro_drive_3d.py`
  and `paint.glsl`: Kuwahara filter, bands that keep each hue, cool and warm tints, Sobel ink).

## Rejected

- Keeping the scratch scripts and rendering their output as images: a picture cannot be placed, scaled or seated at, and
  a still ignores the scene's palette.
- Filling the strokes themselves: the lines stay unfilled paths and the surfaces are a separate plate, so the one look
  without a plate (lines only) keeps working and the plate can be left out.
- Fading the person's torso into the car with a gradient slab: it read as a smear. With plates, the lower half of the
  car (plate and lines) is drawn in front of the person and the upper half behind, split at the belt line by `rows`;
  the plate is solid, so no panel is painted.
- Smooth shading per pixel: four flat tones per material read as drawn, and keep the picture inside a few colours the
  finish and the palette gate can check.
- Fitting every close-up to the model: the person's head would change size from shot to shot.
- Turning the wheel by rotating a picture of it: the spokes would turn but the tread, the hub and the shading would
  not, and the wheel would not sit in the arch. The wheel's geometry is turned and projected again.
- Projecting these models into 2D plates to stand in for a 3D scene (the first pilot, `pedro_drive_toon`): the
  perspective is faked per layer, the wheels and the head are swapped pictures, the occlusion between a person and a
  car is a cut at a guessed row, and the camera cannot move. Real meshes under a real camera give the perspective, the
  occlusion and the shadows for nothing, and the paint-over is one shader on the finished picture, not a recipe per
  layer. The plate path stays for pieces that want drawn lines.
- A level belt line in perspective: a flat cut at a guessed height missed the door's top by 95 px in the close-up. The
  edge is measured.

## Limits

- The projection costs seconds at a wide raster, so each drawing is cached per seed, view, size, distance, wheels and
  spin: a wheel at eight angles is sixteen more projections.
- A prop draws from a fixed set of named cameras (`VIEWS`); a free camera is the `yaw` and
  `elevation` arguments of `project`, not a prop argument.
- No clip is used: the cut is by rows. A person taller than the frame is the caller's to crop.
- A plate is flat shaded per quad, so the facets of a curved wing show as steps; its edges are not antialiased; there
  is no cast shadow and no depth buffer shared with the character. The character is not a model: the piece converts
  Pedro's plates to the same bands with the engine's gradient-map through a stepped ramp and an ink ring behind him,
  an effect recipe and not a part.
- A wheel's tread notches repeat every 2π/48, not at the spoke pitch, so a wheel drawn at a few angles shimmers where
  its layers change. Facets are not blended across quads: smoothing the normals within a material and a crease angle
  is the next step for a curved wing or a bonnet.
- The engine's motion blur did not change a 3D object in a still, so the 3D pilot has none; it keeps the car's cruise
  at 9 m/s so a wheel turns 14 degrees a frame, under half a spoke gap, by calculation, not seen in motion.
- The paint shader's radius turns small features (his eyes in a close-up) to dots, tuned by eye on the pilot and not a
  property of the meshes. The blazer's darkness is not the shader's: with the finish removed it measures a luma of
  0.119 raw and 0.122 painted, so it is the light or the material.
- Coverage of the plate path is by the wire tests; the layered piece (`pedro_drive_toon`) is a pilot, not a part.
