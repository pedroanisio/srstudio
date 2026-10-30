---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0044: A Toon character drawn like the traced cat, in code

- Status: proposed (2026-10-30), amended the same day with a second pass the operator asked for after the first
  comparison. The operator decides from the comparison sheet whether the approach goes on to the raccoon and the
  hedgehog. Implemented for the fox: `toon_cast.Drawing` (with `tilt`), `Look.drawing`, `toon_inked.FOX_INKED`,
  `brush.inked`, `brush.Hand` (with `ragged`), `brush.wobble`, `brush.broken`, `brush.lump`, `toon_wear.Face.tilt`;
  `tests/test_toon_inked.py`, `tests/test_brush.py`, `tests/test_toon_wear.py`.
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
4. **Second pass: rough and simple, like the cat.** The first pass still read as clean digital ink, with busy
   detail. The operator asked for these changes:
   - **Broken line.** `brush.broken` splits the pressed band into seeded pieces. Each gap is about 1.5 line weights,
     the band tapers into it, and a nick is bitten in each piece. Every piece's inner edge sits under the fill. The
     body breaks in four places; the ears, the tail and the paws break in three.
   - **Grit.** `Hand.ragged` adds a fine, high-frequency grit to the band's width. It is zero by default, and every
     existing hand draws byte-identically.
   - **One-off eyes.** `brush.lump` is a seeded blob through a few jittered points. Every iris, pupil, shine and
     the nose highlight is one, seeded by the part, the kind and the side (`zlib.crc32`, not `hash`). Each eye's
     almond is jittered the same way, so no two kinds share a shape and nothing on the face is a perfect ellipse.
   - **Lumpier inner lines.** The inner lines wobble off their points and press unevenly.
   - **A shade that turns the head.** The head shade is a crescent. It starts and ends on the outline and swells to
     24 px into the cheek, so it turns the head instead of striping it.
   - **Less detail.** The second pass cut the crown parting, the chest tufts, two of the four ear fluffs and the
     shade stroke under each arm. Six inner lines remain where there were thirteen.
   - **Wear follows the tilt.** `Drawing.tilt` reaches `toon_wear.Face.tilt`. `wear_layers` draws the items on the
     face levelled about the eyes' midpoint, then turns them with the head. A face with no tilt takes the old path,
     so no other look's wear changes.
   - **Seeded.** Every random choice is seeded, so builds stay deterministic.
   - **The critters' kinds.** `sleepy` eyes and the `yawn`, `scream` and `puff` mouths, which the sloth, goat and
     hamster add to the vocabulary, are drawn for this face, not delegated to the shared drawings. Those use perfect
     ellipses and an even line, so delegating would break the inked face. A kind the face has no drawing for is
     still refused by name, never drawn by a silent fallback.
   - **Shoulders like the cat's.** The operator saw the arms rise from the shoulders as tapered lobes, "like
     pointers". The cat is one contour from head into shoulders into body, its arms an inner line. The shared arm
     paths start on the brush silhouette's edge, so a full-width arm with a round cap stood out of the body there,
     in a notch under the ruff. The inked silhouette now runs from the ruff into the shoulders and the flanks in one
     gentle curve (no turn sharper than 30°, under 150° in all, either side). The left side lost its lowest ruff
     tip for it. The arm leaves the body inside the shoulder (`TUCK`), slim there and widest at the forearm and paw
     (`ARM_TAPER`). An arm whose next point is outside the body bends at an elbow inside it first, so a reaching
     forearm leaves the flank below the shoulder. Its ink follows each edge only where the edge lies outside the body,
     deep inside it (the overlap line) or crosses the body's edge (`_arm_lines`). Where the edge runs just inside the
     flank and along it, there is no ink, and the arm and the body read as one form. Paw targets and the shared arm
     code are unchanged, so typing still reaches the laptop.

## Alternatives rejected

- **Polish fields on `Look`** (an iris colour, a tilt, a shade). The face drawings are what separate the cat. A
  field can place a shared template but cannot redraw it, and every new field would branch every shared part.
- **Tracing a fox.** There is no reference reel for one. This decision tests how close code can get.
- **Breaking the ink band into separate strokes** was rejected in the first pass to save shapes. The comparison
  showed the unbroken band read as digital, so the second pass breaks it. Each piece's inner edge stays under the
  fill, so the fill's edge stays organic and a gap shows the coat at the outline, as a lifted brush does. It costs
  two to three shapes per contour.
- **Rotating every worn item about the neck.** The eyes already sit on the turned head. Turning the items about the
  eyes' midpoint after levelling the face puts the lenses back on the eyes exactly.
- **Drawing the arm inside a clip of the body.** Clipping hides the lobe but keeps the arm's outer ink doubling
  the flank. Inking edges by how they sit against the body draws one contour.
- **Moving the shared shoulder points.** The brush cast and the published reels draw from them, and they must stay
  byte-identical. The inked drawing moves its own arm's start instead.
- **Random jitter.** A build must draw the same line every time, so the drift is a fixed function of the position
  along the contour and a seed.

## Consequences

- A look drawn this way costs more to render. On the comparison sheet's eight poses, the second pass draws 62–73
  shapes and 2,228–2,768 cubic segments per pose; the first pass drew 58–69 shapes and 2,086–2,562 segments. Over
  every kind of eyes, mouth and arms, the second pass draws 54–81 shapes per pose (first pass 50–77). With the
  shoulder pass, one expression in each of the seven arms poses draws 66–72 shapes and 2,549–2,817 segments, and
  every kind of eyes, mouth and arms 54–83 shapes and 1,983–3,247 segments. The broken
  bands add shapes and the cut lines remove some. The brush fox draws 29–46 shapes and 1,028–1,550 segments, and the
  traced cat 23–26 shapes and 493–525 segments. The engine renders every still of the sheet cleanly.
- Every vocabulary kind needs a drawing in each inked face. A kind added to `EYES` or `MOUTHS` fails the inked
  fox's tests until it is drawn for that face.
- A head turned by its drawing turns what it wears too. Another drawn look gets this by giving its drawing a
  `tilt`.
- `brush.broken`, `brush.lump` and `Hand.ragged` are general brush tools, and any character drawn in code can use
  them.
- Hanging arms (`sigh`) lie along the flanks, so most of their edge merges with the body and little arm line
  shows. A leaning arm that hangs outside the body keeps a full outline.
