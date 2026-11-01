---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0104: Bento's hands are a pair

- Status: accepted (2026-11-01), by the operator on the proof at
  `generated/character-proofs/bento-hands/index.html`: "approved"
- Deciders: the operator; ordered by arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0062](0062-bento.md), [ADR 0047](0047-character-versions.md) and [ADR 0089](0089-news-hands-are-a-pair.md)
- Back to the [library README](../../README.md)

## Context

Version 1 of `toon-bento` draws one open paw and one fist on both arms. The open paw's thumb is on its +x side, so a
raised hand on the frame's right shows its thumb outward with the palm to the camera: a second right hand. arc4d3's rule
for the News anchors applies to him too: the right hand is the mirror of the left, and a hand's thumb follows its side,
with palms to camera both thumbs inward and backs to camera both outward.

A gesture held its hands as `(x, y, angle, fist, scale)` tuples in no fixed order, so nothing recorded which arm a paw
was on. The hand on his heart and the hand on his face lie near the middle of the frame and belong to the frame's right
arm, so the side of the frame does not answer it either.

## Decision

Version 2 of `toon-bento` makes the hands typed pairs.

- `toon_bento.Paw` replaces the tuple. It names its `Arm` and its `Facing`, and `Paw.mirrored` is worked out from them
  against `DRAWN_FOR`: a caller cannot choose it. The back of a hand is the mirror of its palm, and shows no crease.
- `Gesture` refuses, when it is built, a hand that is not a `Paw`, a hand closer to the other arm's sleeve than to its
  own, two hands on one arm, and sleeves out of frame-left, frame-right order.
- A hand mirrors across its own wrist (`_WRIST_X`), so it stays on the cuff version 1 fitted it to.
- Hands pressed to him or to a surface show their backs: the hand on his heart, the hand on his face, and every hand of
  the shared poses. A hanging hand shows its back too.
- The paw's ink goes right round it. `_edge` stopped short of its start, because `brush.stroke` drops a last point that
  repeats its first, and left a gap at the wrist. `_ringed` laps past the start. `_edge` stays as it is: version 1 and
  every other outline of his are drawn with it.
- `toon-bento@2`'s specimen draws his nine gestures after the shared arms (`specimens.OWN_ARMS`). Version 1's specimen
  draws only the shared arms, so its digest cannot see a gesture's hands, and a test pins version 1's gestures to a
  sha256 taken before this change.

The inward and outward of the rule are for fingers up. A hand turned fingers down keeps its side and its face, so its
thumb reads the other way: his hanging hand shows its back with the thumb in, toward his leg. The only way to read
"back, thumb out" there is the other arm's hand.

The paws drawn whole in `ready`, `folded` and `tablet` have no thumb, so they have no side to follow. They are version
1's shapes in version 2.

Version 1 keeps drawing its one hand, with its digests unchanged. Nothing in a reel can reach version 2 until it is
approved: `parts.resolved` stays at 1 and `parts.pin` refuses it.

## Alternatives rejected

- A second drawn hand per shape: two drawings to keep alike, the fault this fixes.
- A `mirrored` flag on each gesture's hand: it is the care this replaces, and nothing would hold it to the arm.
- Reading the arm from the side of the frame a hand is on: the hands on his heart and face sit on the axis.
- Fixing `brush._dedupe`: every stroked closed shape in the library goes through it, so every approved digest of those
  would move.
- Changing version 1 in place: an approved version is immutable.
