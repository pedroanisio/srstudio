---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0006: The Stick style — traced stick figures on painted sets, badge heads, outlined captions

- Status: accepted and implemented, 2026-10-28 (`srstudio.stick`, `styles.STICK`, `canvas.DAYLIGHT`,
  `tests/test_stick.py`, `episodes/check_with_my_team.py`, fidelity case `check-with-my-team-1.0.0`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator handed over the package `check-with-my-team-1.0.0` and, once it was voiced and scored, asked for its
style as a library of its own. Until then the episode played the package's `scene.xml` as it shipped and only added
audio (`srstudio.dub`), so the catalog listed it under no style and nothing in it could be reused.

The look is unlike the four styles that exist. Its characters are stick figures in heavy near-black ink: a seated
figure in a study, and a row of dancers in a garden whose heads, but the leader's, are badges: a coloured face
(rounded square or circle) with an icon drawing. Every pose is traced from the reference at 12 fps and swapped on a
contiguous timeline; the dancers share one traced body, offset to each measured head centre, and the badges tilt
with one measured head angle. The two sets are drawn geometry: flat shapes in warm, desaturated tones, outlined in
one brown line colour, with gradients for wall, sky and grass, and traced foliage plates. Captions are font text
(Inter Bold) in white with an ink outline outside, one line per cue; the hook and the headline are traced lettering.
Portrait 1080×1920 at 24 fps on the project clock, no camera move, no sound in the package.

## Decision

1. **Style `STICK`, palette `DAYLIGHT`.** Ink `#070708` (legs, caption outline), white `#ffffff` (caption text),
   shade `#665541` (the line every set shape is outlined in) on a `#bda77a` wall. The caption font is Inter Bold,
   a Google Font (`GoogleFont("Inter", 700)`, OFL-1.1, `fontPolicy="pinned"`). Accessibility defaults are the
   package's. `silent=True`: there is no mouth model, and a voice is narration over the captions. Parts live in
   `srstudio.stick`.
2. **Parts are driven by measured data, and the data is parsed, not trusted.** `stick.load_poses`, `load_icons`,
   `load_lettering`, `load_plates` and `load_script` parse the package's JSON into typed records (`RoomPose`,
   `YardPose`, `Icon`, `Plate`, `Line`) and refuse unknown or missing fields, wrong types, a shot that is neither
   room nor yard, poses that are not back to back, points that are not pairs, fills that are neither a colour nor a
   `url(#paint)`, paths that do not start with M, a changing number of dancers, overlapping or empty captions and
   non-positive sizes (`StickDataError`).
3. **Badges are the episode's data.** `stick.Badge` is a face colour, a radius (or `None` for a round face), an
   `Icon`, the head angle the icon was traced at, and an optional gradient it fills with. The library draws any
   badge; which logos, colours and shapes an episode uses is in the episode script (`check_with_my_team.FACES`), so
   no third-party mark is part of the library.
4. **Drawing conventions are functions, so a rebuilt scene matches.** `stick.shape` draws a frame-sized even-odd
   path, clear unless filled, stroked with round caps only when a width is given, in the shade unless another
   stroke is named; `stick.box` always writes a `radius`; `stick.oval` is unstroked; `stick.paint` defines a
   user-space gradient (`units="user"`, no interpolation space) once, where it is first used, so the order of
   `<paints>` follows the drawing. Ids come from `flat_counter("n")`.
5. **The sets are parts.** `stick-room` (window, wall picture, bookcase, chair, desk, laptop) and `stick-yard`
   (sky, trees with traced foliage, a board fence whose jitter follows the episode seed, grass and tufts) are
   registered locations, so another Stick episode can stage in them; `stick-figure` holds the traced poses;
   `stick-hook`, `stick-headline` and `stick-captions` letter.
6. **The port is verified like the others.** `episodes/check_with_my_team.py PROJECT` builds with `signature=False`
   (the package predates ADR 0001) and the fidelity test compares all 3 470 elements with the shipped scene and the
   SRT with the shipped file. `--voice` builds the same picture as `scene.silent.xml` and dubs the voice-over and
   the music into `scene.xml` with `srstudio.dub`, ending at the loop point; the unpack step no longer copies the
   package's scene or render.

## Rejected alternatives

- **Tagging the episode with an existing style (Cel).** Rejected because Cel's traced fills have no outline, its
  captions are lettering in boxes with no font, and it has a measured camera; Stick has stroked ink legs, font
  captions with an outline, drawn sets and badge heads. A tag would describe the look wrongly and give no parts.
- **Keeping the package scene and only dubbing it.** Rejected because nothing could be reused and the catalog could
  not say which style the episode is; rebuilding it is what makes the parts trustworthy (element-for-element match).
- **Logos in the library.** Rejected: they are the trademarks of their owners and the reference's choice; the
  library draws badges from any `Icon` the episode loads.
- **Reusing `cel.parse_drawing` for plates.** Rejected because Cel refuses a `url(#paint)` fill, which a badge
  drawing uses; the Stick parser accepts colours and paint references and nothing else.
- **`Canvas.grad` for the gradients.** Rejected for the port because it writes `interpolationSpace="srgb"` and no
  `units`, which breaks the element-for-element match; `stick.paint` writes what the package wrote.
- **Naming it after the set or the joke (*Team*, *Garden*).** ADR 0002 names styles after their drawing technique;
  stick figures over painted sets is the technique, the garden and the team are one episode's content.

## Consequences

- A new Stick episode needs traced poses and the badges it wants; the sets and the captions come with the library.
- The catalog lists the episode under Stick, and `srstudio catalog --style stick` lists six parts.
- The package's character art, dialogue, lettering and the reference's choice of logos are adapted from the
  reference and stay their authors'. The library keeps the style, the loaders, the sets and the conventions.
