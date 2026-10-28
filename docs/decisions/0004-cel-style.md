# ADR 0004: The Cel style — traced drawings under a measured camera, silent, lettered captions

- Status: accepted and implemented, 2026-10-28 (`srstudio.cel`, `styles.CEL`, `canvas.LINEN`, `canvas.flat_counter`,
  `Timeline.from_captions`, `tests/test_cel.py`, `episodes/mushroom_training.py`, fidelity case
  `mushroom-training-2.0.0`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Fable 5.1 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator handed over a fourth package, `mushroom-training-2.0.0` ("Work Training Be Like — Silent Visual
Match"), and asked for its look as a style of the library. The package is unlike the three styles that exist: it is
portrait 1080×1920 at 24 fps, it has no sound, no font and no text layer, and nothing in it is drawn from
parameters. Its character is a set of traced vector contours per drawing, swapped on a measured timeline of runs; its
camera is two series of samples every 0.25 s (one for the character, one for the room) measured from the reference;
its captions are the reference's lettering kept as filled glyph paths inside teal boxes. The only drawn geometry is
the room: a wall, a plank floor fanning from a vanishing point and a desk.

A style in this library is a value plus a module of parts, and a port is verified by rebuilding the shipped
`scene.xml` element for element (`tests/test_fidelity.py`). Three things in the library stood in the way: every
episode added a caption font asset (and so an `<assets>` element), every style needed a mouth model per palette,
and `Timeline.load` read only phrase or take files.

## Decision

1. **Style `CEL`, palette `LINEN`.** Portrait 1080×1920 at 24 fps on the project clock. `LINEN` is ink `#240102`
   and white `#fffaf5` (the lettering) on a `#c5bbb0` wall; its shade is the lettering-box teal `#2b87ab`, the one
   mid tone the style uses. Accessibility defaults are the package's (`flashCheck="error"`, contrast and legibility
   `warn`). Parts live in `srstudio.cel`.
2. **A style can be silent and font-less.** `Style.font` may be `None` and `Style.silent=True` lifts the
   one-mouth-per-palette rule; `EpisodeSpec` then resolves every font field and `mouth_style` to `None`,
   `Episode` adds no font asset, `Canvas.text` is refused with a message naming the cause, and `Episode.mouth`
   raises `TypeError` before anything else. `Canvas.assets` is created on first use, so a scene with no font, audio
   or text has no `<assets>` at all, which the fidelity comparison requires. Scenes that do use assets are
   unchanged: the SDK serialises top-level elements in schema order.
3. **Parts are driven by measured data, and the data is parsed, not trusted.** `cel.load_camera`, `load_runs`,
   `load_drawings` and `load_captions` parse the package's JSON into typed records (`CameraKey`, `Run`, `Fill`,
   `Caption`/`Box`) and refuse unknown fields, wrong types, non-increasing times, non-positive scales, gaps or
   overlaps between runs, overlapping captions, captions without boxes, glyphs that are not paths and fills that
   are not colours (`CelDataError`). The parts take the records: `cel.world` keys the measured camera on the group
   everything is drawn in; `cel.room` draws the set under the room's own camera re-expressed inside the world's
   (`cel.compensate`: scale `r/q`, offset `(r − q)/q.scale`, which must be sampled at the same times); `cel.traced`
   holds one drawing per run in a group alive from the run's start to its end; `cel.lettering` draws a caption's
   boxes in the shade and its glyphs in white.
4. **Drawing conventions are functions, so a rebuilt scene matches.** `cel.shape` draws a frame-sized path with
   `fillRule="evenodd"`, unstroked unless a width is given and round-capped when it is; `cel.block` draws a rect
   without `radius` (`Canvas.rect(radius=None)`); `cel.anim` writes linear keys on the local clock with values
   rounded to five decimals and the last measured key held to the end of the project. Ids come from
   `flat_counter("v")`: one counter and one prefix for every node, which is the package's `v1…vN` scheme.
5. **The input of a silent episode is its caption script.** `Timeline.from_captions` reads a list of
   `{start, end, text, caption?}` as caption phrases, in order and non-overlapping, and the project lasts until the
   last one ends. A caption without its own text is the spoken text without its ellipsis, which is the rule the
   package's SRT follows; `subtitles.write_srt` then reproduces that SRT byte for byte.
6. **The port is verified like the others.** `episodes/mushroom_training.py` builds with `signature=False` (the
   package predates ADR 0001) and the fidelity test compares all 2 300 elements with the shipped scene and the SRT
   with the shipped file. The engine validates the result and renders it (1053 frames, 43.875 s).

## Rejected alternatives

- **Font-based captions for the style.** Rejected for the port because the shipped scene has lettering as paths and
  no font, and a `<font>` asset alone would break the element-for-element match. A Cel episode that wants text sets
  `EpisodeSpec.font` itself; nothing in the style forbids it.
- **Converting the traced poses to the Soft rig.** Rejected because the drawings are the reference's contours, not
  limbs of fixed topology; a rig would redraw the character and lose the look the operator asked for.
- **Loading the measured files in the episode script.** Rejected because the parsing and its refusals are what
  makes the next Cel episode safe to write; in the script they would be copied, not reused, and untested.
- **A `duration` field on `EpisodeSpec`.** Not needed: a caption script ends with its last caption, and the
  package's does end exactly at 43.875 s. Style decisions stay in `Style`, not in new spec fields.
- **A mouth model placeholder for silent styles.** Rejected because a control that cannot fail is not a control;
  `silent=True` says what is meant and `mouth()` refuses.

## Consequences

- A new Cel episode needs measured data: camera samples, a run timeline and traced drawings. The library draws
  from them and refuses malformed ones; it does not trace.
- `Canvas.assets` is lazy. Code that needs the element calls the property, as before; nothing may assume it exists
  in an empty scene.
- The package's character, dialogue and lettering are adapted from the Under Studio reference and stay their
  author's. The library keeps the style, the loaders and the conventions.
