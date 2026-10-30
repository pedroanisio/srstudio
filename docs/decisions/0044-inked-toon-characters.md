---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0044: A Toon character drawn like the traced cat, in code

- Status: proposed (2026-10-30). The operator decides from the comparison sheet whether the approach goes on to the
  raccoon and the hedgehog. Implemented for the fox: `toon_cast.Drawing`, `Look.drawing`, `toon_inked.FOX_INKED`,
  `brush.inked`, `brush.Hand`, `brush.wobble`; `tests/test_toon_inked.py`, `tests/test_brush.py`.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0014](0014-toon-brush-characters.md) and [ADR 0041](0041-toon-cast-expressions-and-wear.md)
- Back to the [library README](../../README.md)

## Context

The traced cat reads as hand-drawn. The brush characters read as clean vector art. Measured side by side, the cat
has six things the brush characters lack:

- uneven, asymmetric contours;
- a line that is heavier at the bottom and back of a shape and thin at its tips;
- inner lines that do not close;
- a slight head tilt and an off-centre face;
- eyes and a mouth drawn for its face;
- one darker coat tone where its forms turn.

Brush characters share one set of eye and mouth templates, placed by a `Look`'s fields. Nothing in a `Look` can
replace them.

## Decision

1. **A `Look` may carry a `drawing`** (`toon_cast.Drawing`). It supplies the look's own foundation (body, ears,
   marks, shading, inner lines), its eyes per kind, its blink lids, its mouths, its visemes and its limbs.
   - `figure_layers` and `figure` call the drawing wherever the shared parts would draw. Draw order, pose
     placement, typing frames, blinks, lip sync, wear and stickers stay with `toon_cast`, so the contract is the
     same for every look.
   - The default is no drawing. Every existing look draws exactly as before; the rebuild proof on the published
     episodes confirms it.
2. **Two brush tools carry the hand.**
   - `brush.inked` is a rim pressed by a `Hand`. The band's width follows the outward normal's angle to a light
     direction, so the line is heavier at the back and bottom. A convex turn thins it toward a lifted tip, and a
     repeatable grain makes it uneven.
   - `brush.wobble` moves a contour across itself by a bounded, seeded drift, so the outline is uneven but the same
     on every build.
3. **The inked fox (`fox-inked`, `toon-fox-inked`) is drawn with them, beside the fox.**
   - Its contours are hand-placed and unmirrored. Its inner lines are open tapered strokes, and one shade tone
     plus a cream shade under the chin turn its forms.
   - The head tilts about the neck, the face sits off the head's midline, and the far eye is smaller.
   - Every `EYES` and `MOUTHS` kind and every viseme is drawn for its face: almond eyes with an iris, a muzzle
     mouth. A kind it has no drawing for is refused by name.
   - The fox (`toon_cast.FOX`) is unchanged.
   - It is cast by name in a sketch, but it is not in `toon_cast.LOOKS`, whose tests assume the shared face.

## Alternatives rejected

- **Polish fields on `Look`** (an iris colour, a tilt, a shade). The face drawings are what separate the cat. A
  field can place a shared template but cannot redraw it, and every new field would branch every shared part.
- **Tracing a fox.** There is no reference reel for one. This decision tests how close code can get.
- **Breaking the ink band into separate strokes**, as the cat's line breaks. A band under the fill keeps the fill's
  edge organic and costs one shape. Separate strokes would multiply the shape count further, and the gaps would
  show the coat at the edge.
- **Random jitter.** A build must draw the same line every time, so the drift is a fixed function of the position
  along the contour and a seed.

## Consequences

- A look drawn this way costs more to render. Per pose, the inked fox draws 58–77 shapes and about 2,100–2,600
  cubic segments. The brush fox draws 29–46 shapes and 1,000–1,550 segments, and the traced cat 23–26 shapes and
  about 500 segments.
- Every vocabulary kind needs a drawing in each inked face. A kind added to `EYES` or `MOUTHS` fails the inked
  fox's tests until it is drawn for that face.
- A head turned by its drawing still takes `toon_wear` items about the `Look`'s face fields. The glasses stay
  level on a tilted head.
