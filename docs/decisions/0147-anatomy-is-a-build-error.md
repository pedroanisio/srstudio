---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0147: A hand on an arm, one pair of arms, a bust that does not stand in the open

- Status: accepted (2026-11-01), ordered by arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0146](0146-hand-chirality-is-a-build-error.md) and
  [ADR 0073](0073-frame-gates-and-standing-review.md)
- Back to the [library README](../../README.md)

## Context

arc4d3: "Make structural errors impossible in the SDK and kit, not caught in review." The rule for bodies: a hand exists
only as child of an arm, one pair of arms per character, and full-figure framing requires legs and feet.

ADR 0073 measures a figure's straight cut on the frame, for any character, at first delivery only, and it says nothing
of what a character is. Seven props draw a hand with no arm behind it, and nothing asks whose it is.

## Decision

`anatomy.Body` says what a character has of a body: a `Framing` and its `arms`. `FULL` has legs and feet, `BUST` stops at
the waist or the chest, and `WHOLE` is all there as drawn: an appliance, a bird, a peg doll on its round foot. Arms are a
pair or none, and a body with no arms, or a `WHOLE`, says why. `anatomy_parts.BODIES` declares every character, a test
reads it against the registry, and a character with hands has arms for them.

Three rules join the two of ADR 0146, in the same ledger, the same list and the check named `anatomy`:

- `hand-no-arm`, at the build. `anatomy_parts.LOOSE_HANDS` lists the props that draw a hand and no arm: `toon-phone` and
  `toon-clipboard` with `hand=`, `toon-lasagna`, `toon-watering-can`, `toon-highlighter`, `toon-folded-sheet` and
  `crayon-cv`. Each draws through `anatomy_ledger.loose_hand`. Run inside `with anatomy_ledger.on_arm("bear", Side.RIGHT):`
  it is on that character's arm, and otherwise `Episode.finish` refuses the reel. `on_arm` changes no drawing.
- `arm-third`, on the frames. A Collage `arm` with a hand and a `reach` record a `Limb` (owner, side, node) in
  `anatomy.json`. Two live hands on one arm of one character on one frame are refused. One hand at a time, as a reel cuts
  between shots, is fine. A hand is on the frame when part of it is drawn inside the frame and not every pixel of it is
  under a solid shape drawn in front; a hand faded out, beyond the edge or wholly behind a wall is not seen, and a hand
  partly seen counts. A shot that parks its earlier hand behind the set while an insert shows another
  (`thought-of-you` at 3.5 s) is one hand on the frame.
- `bust-open`, on the frames. A figure declared `BUST` whose bottom is a `figure_gates.Cut` that `refused` holds, and
  which drew no `-legs` group of its own, is refused, and now at the build. ADR 0073's check stays as it was for every
  figure at first delivery. An undeclared character is refused, never passed.

`srstudio build` runs the two frame rules after a build (`anatomy_gate.after_build`) and exits 1 on a fault. They need
the engine's frames: a build with none prints that the frames were not measured. `anatomy_gate.body_defects` runs them
at first delivery in `episodes/instagram_posts.py` either way, where a scene with no `figures.json` is refused.

The pictures did not move: specimen digests, every Collage pose, every Bento gesture and Rafa's mesh compare equal to
the tree before the change. `fitted-sheet`, held and unpublished, now names the bear's arm.

## What it would have caught

Counted on what is already built:

- `hand-no-arm`: 10 reels, found by walking the episodes' syntax trees for each prop's call, with `hand` read from its
  keywords. A test keeps that walk equal to the list. 9 are published and are rows of the list: `baby-monitor`,
  `do-you-floss`, `entry-level`, `get-your-mother`, `its-soaking`, `nine-alarms`, `text-me`, `texts-back`, `voice-note`.
  `fitted-sheet` is not published, so it now says whose hand it is.
- `bust-open`: 0 of the 102 current scenes with a figures record, run through the real measure on the engine's frames.
  133 more scenes leave no such record, so they are not measured. The same cut measure refused `ill-get-this` in ADR 0073,
  on the scene as it was before its fix.
- `arm-third`: not measured. A build before this rule recorded no limbs, and one rebuild, `sensor`, showed none.

## Limits

- `arm-third` sees only `Limb`s. A third hand against a character's own pose arms is not seen, because Collage pose hands
  and Cutout's `reach` record no owner. Toon props return no node, so they carry no limb id either.
- One pair of arms is declared and is enforced at those limbs. Nothing counts arms in a drawn pose.
- `on_arm` is a declaration, as `side=` is: a caller who names the wrong character is not caught.
- A pilot is not built by `srstudio build`, so neither frame rule runs on it, and `episodes/publish_pilots.py` reads no
  record. `hand-no-arm` still refuses in `Episode.finish`.
- The frames are `framegraph`'s, so layers and effects are not read, as in ADR 0073.
- A Cutout head-only call in a video tile is measured as a `BUST` part, with its body drawn by scene code. None of them
  was refused on the built reels.

## Alternatives rejected

- A raise in each prop: published reels must stay rebuildable, and those props are in them.
- A `hand` that needs an `Arm` argument: every call in a published reel would change, for a value the prop does not draw.
- Giving the frame rules the build's own bytes without the engine: where a figure ends is only known on the frames.
- A second bust measure with no flatness test: on the built reels it refuses head-only calls whose cut is a neck.
- Counting `FULL` figures: Stick figures are strokes with no fill to end, and their hits would be noise.
