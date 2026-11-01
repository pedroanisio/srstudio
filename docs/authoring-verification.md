---
updated-by: OpenAI Codex (GPT-6)
---

# Verify scenes, motion and delivery

[Library README](../README.md) · [Authoring task index](authoring-reference.md)

Choose tests matching the behavior changed: data validation, authored geometry, temporal sampling, rendered output or delivery. The inventory below records each suite’s scope. [Composition checks](composition-preflight.md), [motion quality studies](../examples/limbs_quality.py) and [authoring benchmarks](authoring-benchmark.md) keep numeric guarantees, rendering cost and perceptual evidence separate.

Run commands from the srstudio repository root.

## Verification

- `tests/test_build.py` builds an office and a café episode from a synthetic project and asserts the SDK, the XSD and
  the Schematron report nothing; it also asserts `finish()` refuses a document with findings.
- `tests/test_ink_layout.py` does the same for the square Ink style from a synthetic `timeline.json`, and for *The
  Router*: the LED chase and voice marks, the power states, the blackout, the hand's three actions, the shelf shots
  with their signature marks, and a ten-take build through `router_scene`; `tests/test_the_router.py` covers the
  audio step's checks (script shape, word and phone timings against the trim, the schedule, the conform to the
  sample, the voice-name check) with mismatched, cut and malformed inputs.
- `tests/test_styles.py` asserts what each style decides, that an explicit field wins, that a foreign palette is
  refused, that a silent style needs no mouth model, and that the registry and the CLI know the style of every part.
- `tests/test_cel.py` covers the Cel style (silent, font-less, one id counter), the caption-script timeline, every
  loader with malformed camera, run, drawing and caption files, the room camera compensation, the drawing
  conventions (even-odd paths, radius-less rects, five-decimal keys held to the end) and a silent build with no
  `<assets>` that the SDK and the engine validate, the tracked-point loader with bad samples and the pressed
  keyboard (subpath split by nesting depth so holes travel with their shape, press keys on the composition clock, a
  plain drawing when nothing is struck, errors for relative paths, bad boxes and an empty box).
  `tests/test_narration.py` covers the narration step's slots, bounded speed-up, placement rules (lead, tempo,
  cut), look-ahead plan, the relaxed plan (natural pace, spill, bounded lag, montage cut, extended duration),
  tempo conform and the manifest check (items, optional `lag`, `effects`, `duration`) with malformed, tampered
  and missing inputs; `tests/test_mushroom_training_audio.py` pins the script to the library steps, the natural
  speed and the respellings; `tests/test_foley.py` covers the keystroke bed (bursts from motion, determinism,
  peak, bounds, the written file).
- `tests/test_stick.py` covers the Stick style value, every loader with malformed poses (wrong shot, unknown and
  missing fields, gaps, bad points, colours and paths, a changing number of dancers), icons, lettering and scripts,
  the drawing conventions (even-odd paths stroked only with a width, rects that always carry a radius, user-space
  gradients defined once), the seeded fence, one group per pose with a badge per dancer, and the outlined captions;
  the rig's pose and head keys, its mouth and closed faces, refused performances, every pose and face, looks
  (every hair, glasses, ties, refused looks), standing, placed and mirrored figures, the camera, the hook card and
  the box its three lines fit, the call screen (inbox, tiles, speaker ring, marked row, refused calls) and the
  caption outline modes; `tests/test_screen_share.py` checks the *Screen Share* script and refuses malformed lines;
  `tests/test_fidelity.py` rebuilds the package's 3 470 elements and its SRT.
- `tests/test_toon.py` covers the Toon style value, the pose and script parsers with every malformed input (unknown
  expressions, out-of-order times, overlapping cues, empty captions, unreadable files), the traced art's parser
  (wrong schema, missing tables, bad shapes, a missing or broken package file), the reference-pixel mapping, the
  room and desk colours and gradient, one group per pose run with every eye, mouth and arm kind drawn, the typing
  frames and their swap keys on the composition clock, the measured caption pills and a canvas without a font;
  `tests/test_brush.py` covers the brush (splines through their points, stroke bands and caps, outline and rim,
  the transforms, refused measures); `tests/test_toon_cast.py` draws every expression of the dog and the frog
  inside their corner, the two typing frames, refused expressions, the groups and swaps, a later entrance and the
  registry entries;
  `tests/test_toon_cast_more.py`, `tests/test_toon_expressions.py` and `tests/test_toon_wear.py` cover the fox,
  the raccoon and the hedgehog (thumbnail heads, coats, builds), the new expressions with the cat's refusal, and the
  wear on every character and through a sketch;
  `tests/test_sketch.py` covers the sketch (checks and every refused inconsistency, cues with speakers,
  appearances, events, line spans, typing bursts, the placement onto a recording, the drawn cast with stickers, the
  written and reloaded files, a recording through a fake client with its manifest, and a misheard line);
  `tests/test_toon_props.py` draws every prop with its keys and refuses bad data; `tests/test_toon_sketches.py`
  covers the two sketches (a question hook, both coworkers, the hold before the punchline, the sting, refused
  events, the dressing of each shot, the badge spans, the recording run's effects and manifest, a voiced project
  whose files disagree, captions too wide for a pill);
  `tests/test_employee_survey.py` covers the reel's data (consistency, every refused inconsistency, cue and pose
  derivation, sentence spans, typing bursts), the placement onto a narration (words, silent beats, the crowded
  beat, the minimum caption hold and its cap, refused takes), the written files and the narration script's
  constants and alignment cut; `tests/test_fonts.py` covers `fonts.text_width` on a real TrueType file.
- `tests/test_signature.py` asserts the two [Signature](authoring-delivery.md#signature) marks are in every location of a signed office
  episode, absent from an unsigned one, typed on a code without glyphs, and gradient-free in the `MONO` palette.
- `tests/test_layout.py` covers safe-area validation, exact path bounds for every SVG command, the overlay check
  against the engine (inside, crossing, hidden, rotated, instanced) and every malformed-input path; `tests/test_symbols.py`
  asserts instanced office angles draw each shape with the same world transform as the inline drawing.
- `tests/test_soft.py` covers the Soft style and palette, top captions, stroke outlines, interpolation and placement,
  the pose sheet, the two-pass silhouette, in-between drawings, rotation-preserving turns, arcs, planted feet,
  overshoot and settle, the cheer, wave and seated-nod poses, that no front arm covers the face in any pose or in-between, every refused cue, the sung
  mouth track, the keyed rig and contact shadow and, on the engine, that exactly one eyes and one mouth of Pip are
  visible at each frame, the seated legs reading as two, the looks (Bo's ids, fills and hairline, Juno's and
  Remy's shade, the shade crescent's geometry, lashes on every eye and catch-lights only on pupils, Pip and Bo
  drawing no polish, the whole cast in one scene without an id clash) and the soft home (the hip on the cushion, the soles and the sofa's front on one floor,
  the lounging hands on the lap, a seated character between the seat and the near arm);
  `tests/test_audio.py` asserts `ep.audio()` builds each source's mix exactly as the explicit calls do, the style's
  master levels, verified narration cues (a tampered clip is refused) and the refused options;
  `tests/test_music.py` covers the beat grid, deterministic and peak-levelled rendering, silent rests, beat-exact
  kicks and every refused setting; `tests/test_fonts.py` covers the request, every refused stylesheet, the font-file
  reader on damaged files, install with offline reuse, a tampered pin, wrong family or weight (nothing written),
  licence fallback, the size limit and the CLI, against a fake fetcher with a real TrueType file.
- Quality gates (`pyproject.toml`): `ruff format --check`, `ruff check`, `mypy src`, and branch coverage of at least 80 %.
  The publish gate runs inside the suite when `SRSTUDIO_RENDERS=/path/to/generated/renders` and
  `SRSTUDIO_FONTS=/path/to/generated/fonts` are set (see Instagram captions).
- `tests/test_fidelity.py` rebuilds the seven shipped episodes from their extracted packages
  (`SRSTUDIO_PACKAGES=/path/to/extracted` with `<name>-<version>/project` inside) and compares them with the shipped
  `.scene.xml` using [tools/compare_scene.py](../tools/compare_scene.py): every element, attribute and text in document
  order, numbers rounded to five decimals, `metadata` ignored, `animate`/`expression` children compared after their
  sibling shapes (the engine evaluates them by property, so their position among shapes does not change the picture).

Rendering needs the scene-render engine (`scene-render encode <slug>.scene.xml`); it is not part of this package.
