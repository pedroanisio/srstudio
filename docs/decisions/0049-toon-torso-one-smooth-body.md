---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0049: A Toon torso: one smooth contour over the shoulders, with the arms drawn inside it

- Status: accepted; implemented 2026-10-30 (`srstudio.toon_torso`: `Torso`, `TAPER`, `UNDER`, `SPACING`, `BULGE`,
  `CURVE_IN`; `arm_lines`, `depth_in`; `brush.wobble(weights=)`, `Critter.torso`; `tests/test_toon_torso.py`,
  `tests/support/toon_contour.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Amends [ADR 0045](0045-toon-sloth-goat-hamster.md) (the sloth, the goat and the hamster)
- Back to the [library README](../../README.md)

## Context

The operator judged the sloth's, the goat's and the hamster's shoulders "like pointers", not as smooth as the traced
cat's shoulder and body. The cause is in how the arm starts. Every arm pose in `toon_cast._arms` starts at the shared
`SHOULDERS` (62, 712) and (308, 712) at full width, on the edge of the body or, on the goat, outside it. So each arm
rose from the body as a rounded lobe, and the lobe broke the silhouette. The outline under it was also drawn by hand
for each critter, so the shoulder line and the arm never agreed on where the shoulder was.

The traced cat has no such lobe. Its head runs into its body in one outline, and its arms are lines inside that
outline.

The older brush cast (dog, frog, bear, rabbit, raccoon, hedgehog) shares the same lobe arms and is to get the same
treatment on a later branch, with every published episode pinned to the old drawing. So the answer has to be a helper
any `Drawing` can use, not geometry belonging to these three.

## Decision

1. **A `Torso` builds the body under a head from a few numbers.** A character supplies its head contour from neck
   join to neck join, the half-width of its shoulders and of its flank, the slope of the shoulder line in degrees and
   the width of its arm. `Torso.contour` is the whole closed outline.
2. **Each side is drawn as a turtle draws it.** From the neck join it runs an arc from the head's own heading into the
   slope, a straight run out to the shoulder, an arc down into the flank, and a straight flank to the base. Every arc
   has a fixed least radius (`BULGE` 54 px out over a shoulder, `CURVE_IN` 48 px in under a jaw). The curvature is
   bounded by construction, so no corner can appear, whatever the numbers. A shoulder so low that no arm fits above
   the base is refused by name (`ToonDataError`).
3. **`Torso.weights` calms the hand wobble on the shoulders and flanks.** `brush.wobble` takes per-sample weights
   (0 to 1). The head keeps its full wobble and fur edges; the torso takes `CALM` (0.15) of it, so a long flank does
   not ripple.
4. **`Torso.arm_path` redraws a pose's arm inside the body.** The top moves under the shoulder line, half an arm's
   width inside the outline. The stroke tapers from a thin crease at the top to full width at the forearm
   (`TAPER`). The paw stays where the pose puts it, so typing still reaches the desk.
   - An elbow that would poke out is pulled in, and further in until the arm clears the outline above the shoulders.
     If it cannot, the arm is refused by name.
   - A point beside the shoulders is moved in toward the chest (`keep`).
   - A paw raised to the face crosses in front of the neck, so only its upper arm has to clear the outline.
   - An arm reaching more than its own width past its flank, as the near arm does when typing, leaves the body on a
     gentle line from the top. An elbow pulled in behind the top would double the arm back on itself.
5. **`Torso.limb` returns the arm's layers, the paw's position and the way it points.** The arm is an ink stroke set a
   little low, the coat over it, and a shade under the forearm. Both strokes taper into the body, so the arm reads as
   a wedge, heavier underneath. The operator approved this wedge on the three reviewed clips. `arm_lines` is the inked
   fox's rule (ADR 0044), moved here from `toon_inked` beside `depth_in` so any drawing can ink an arm that way: an edge
   is inked where it leaves the body or lies well over it, and never within `SEAM` widths inside the body along the
   flank. The fox keeps its own arm path (`TUCK`), because its silhouette is traced by hand and is not a `Torso`. The
   paw itself stays the character's own drawing. A `Drawing.limb` calls `Torso.limb` and appends its paw.
6. **The critters' fur strokes at the arm joints are gone,** because no joint is left to mark. Their heads keep their
   contours except for the last neck points of the sloth and the goat, moved so that the two shoulders sit within
   10 px of each other's height. Each head is tilted, and the arc from a leaning neck otherwise drops one shoulder
   and lifts the other.
7. **The older brush cast is unchanged.** It keeps the shared `_limb` arms, byte for byte, until its own branch.
   `Torso` draws only for a `Drawing` that builds one.

## Alternatives rejected

- **Hand-placed Bezier sides.** They turned 34° to 38° at the neck and could turn back up at the shoulder. Each new
  character would need the same tuning again.
- **Filleting a polyline and refusing radii that do not fit.** The set of numbers that passed was far too small to
  draw three different builds from.
- **Keeping the lobe and softening it** with a shade, or a stroke over the join. The lobe is the defect: the top of
  the arm would still sit on or outside the outline.
- **Changing `toon_cast._limb` for everybody.** Every published older character would change. Published reels are
  frozen.
- **A separate slope for each side.** It adds a number to every character to correct what a small change at the neck
  join corrects once.

## Consequences

- A `Drawing` with a `Torso` gets a smooth body and arms that sit inside it in every `ARMS` pose, with the guarantee
  tested on its outline: no outward turn over 10° per 8 px and no inward turn over 15° per 8 px on the ink rim and the
  coat, and at most one change of bend down a side.
- The goat's forearms in `face` and `face2` run outside its neck silhouette, in front of it, because the neck is
  narrower than the paws' spread. The test exempts points between the shoulders when a paw is drawn over the face.
- The sloth, the goat and the hamster are redrawn. They appear in no episode yet, and the older cast is untouched, so
  the published episodes rebuild as before.
- `toon_critters.pressed` tightens a concave curve on the inner edge of its band, so the critter test's inward limit
  (15° per 8 px) is looser than the `Torso` unit test's (13.5°).
