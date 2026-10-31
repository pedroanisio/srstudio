---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0059: Head rigs for the redrawn six, with an open chin

- Status: proposed (2026-10-31). The operator asked for the rigs ("build rigs"). Each rig stays proposed, and refused
  to a reel, until the operator judges its clip. Implemented: `DOG_RIG` to `HEDGEHOG_RIG` in `srstudio.toon_redrawn`,
  their six `HeadStyle`s, `Split.open_chin` and `shade(only=)` in `srstudio.toon_critters`, the six `rig` records on the
  `toon-*` version 2 records; `tests/test_toon_redrawn.py`.
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0047](0047-character-versions.md), [ADR 0050](0050-organic-head-motion.md) and
  [ADR 0052](0052-older-cast-version-2.md)
- Back to the [library README](../../README.md)

## Context

The dog, the frog, the bear, the rabbit, the raccoon and the hedgehog were redrawn as version 2 with one smooth body
and no line between head and body: the coat runs from the crown down past the neck. Their records hold `rig: null`, so
`heads=` refuses them.

A head rig separates a head from a body so that the head can turn, and the seam has to hide somewhere.
[`toon_head`](../../src/srstudio/toon_head.py) offers two places: under a ruff, the top of the body drawn over the head,
or under the head's own chin. These six have no ruff, and an inked chin would change the approved character: it would
draw a jaw across a neck that has none.

Two facts of the rig set the rest:

- A rig turns its whole head about the neck, where the flat drawing's tilt fades out above it. A line placed under the
  flat chin would sit in the wrong place, so the chin is placed where the head sits at rest and turned back by the tilt.
- Published reels and the four approved rigs must not change a byte. Whatever the rig adds has to be off by default.

## Decision

1. **The head is drawn over the body, and its lower edge is the chin, with no ink.** `Split(open_chin=True)` keeps the
   coat as the head's fill and stops the outline at the two neck joins. At rest, head and body are one colour and the
   chin is invisible. When the head turns, its edge shows as the fold between two areas of the same coat.
2. **The outline tapers out at the joins.** The ink turns inside the head just above each join (`CHIN_PEEL`), and a
   tapered stroke under the fill (`CHIN_TAIL`) carries the visible line to the join. A hard stop made a tick there, and
   stopping the ink early left a stretch of bare fill.
3. **The chin runs above the belly.** Each chin is traced just over the top of the character's belly or chest, so the
   head cannot hide what the flat drawing shows. A test holds that at rest.
4. **Shade follows the outline, not the chin.** `shade(only=)` stops the head's shade at the joins, so no band of shade
   runs along an edge that carries no ink.
5. **The neck runs up behind the head's own edge.** Each `top` starts on the head's outline, so turning the head never
   shows a gap between the body's ink and the head's.
6. **Each character moves its own way.** `HeadStyle`s, with the seed unique across all rigs: the dog eager and bouncing,
   the frog still and then sudden, the bear heavy and slow, the rabbit alert and quick to glance, the raccoon shifty,
   the hedgehog timid, flinching before it moves.
7. **Rigs sit at version 2, and version 1 has none.** A published reel draws version 1, and it stays refused to `heads=`.
8. **Every rig starts proposed.** `rig_of` refuses a proposed rig. Only the operator's decision, recorded with its
   words, makes one approved, and until then its digest guards nothing.

## Alternatives rejected

- **A band of coat over the join, with a throat patch below it.** This was built first. The chin's ink stopped in stubs
  at the neck corners, and the patch cut steps into the bellies.
- **A ruff or collar on each character.** It would hide the seam, and it would change six approved drawings.
- **An inked chin line.** It would read as a jaw the drawing does not have, and it would show at rest.

## Consequences

- Reels can name the six in `heads=` as soon as the operator approves each rig, one at a time.
- `Split.open_chin` is available to any `toon_torso` character with a body that hides nothing at the neck.
- `shade(only=)` and `open_chin` default to the old behaviour, so the sloth, goat, hamster and fox rigs keep their
  digests, and the flat version 2 drawings keep theirs.
- At the deepest nod the chin's edge crosses the belly in a small corner. That is a limit of a rigid head over a body
  that does not move, and it shows only at the bound.
