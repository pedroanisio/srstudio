---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0144: Hand chirality is a build error

- Status: accepted (2026-11-01), ordered by arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0142](0142-news-hands-are-a-pair.md), [ADR 0143](0143-bento-hands-are-a-pair.md) and
  [ADR 0073](0073-frame-gates-and-standing-review.md)
- Back to the [library README](../../README.md)

## Context

arc4d3: "Make structural errors impossible in the SDK and kit, not caught in review." The rule for hands: the right hand
is the mirror of the left, and a hand's thumb follows its side; palms to camera, both thumbs point inward; backs to
camera, both point outward.

The News anchors and Bento were each fixed with a contract of their own, Collage had a `side` that defaulted to the
frame's left, and Rafa worked its thumb out by hand. A reviewer caught the rest on frames. The measure below is what
that cost.

## Decision

`srstudio.anatomy` is the one contract. `Arm` carries a `Side` and a `View`, since a POV arm, seen by the camera looking
down it, inverts. `Arm.hand(facing, fingers)` gives a `Hand` whose thumb is worked out, never chosen, and a `Hand` put on
another arm is a `HandError`. A `Drawing` names the arm and facing a drawing was made for, and `Drawing.mirrored(hand)`
is the one answer to whether it is flipped. A hanging hand reads back with the thumb in: `Fingers.DOWN` says so
explicitly. A hand with no thumb is a `Thumbless`, which has to say why, so ready, folded and tablet poses state it
rather than skip it.

News, Bento, Collage and Rafa draw through it. Their pictures did not move: specimen digests, every Collage pose, every
Bento gesture of both versions and Rafa's mesh compare equal to the tree before the change.

`srstudio.anatomy_parts` declares every character and every part that speaks of a hand: paired, single (with the side
and facing of its one drawing), thumbless (with why) or none. A test reads it against the registry, so an undeclared
part fails, and `NOT_A_HAND` is the closed list of names that only sound like one.

An approved version is immutable and stays drawable, so a draw site that cannot refuse notes the fault on its `Canvas`:

- `hand-unpaired`: a version with one drawing on both arms, `news-gus` and `news-vera` 2 to 5, `toon-bento` 1.
- `hand-no-side`: a Collage arm with a hand that does not say its `side`. It is drawn as it always was.

`Episode.finish` refuses the reel before any scene is written, as `AnatomyRefusedError`, unless a row of
`assets/anatomy_published.json` excuses that reel, rule and part. The list is closed and typed: unknown fields, a row
twice or a rule that does not exist are refused, and a test walks `episodes/` so the Collage rows are exactly the reels
that still leave `side` out.

The check is named `anatomy`. `srstudio build` leaves `anatomy.json`, and `anatomy_gate.hand_defects` reads it at a
reel's first delivery in `episodes/instagram_posts.py`, beside the frame gates. Any note stands there, whatever the list
says, because the list is for what is published and a first delivery is not. A scene with no record is refused until
it is rebuilt. `srstudio anatomy` prints the list and marks a row whose reel no manifest names.

## What it would have caught

Counted on what is already built, without rendering:

- 12 of the 14 delivered News reels drew an unpaired version in their first package, read from each package's hand
  scales: a hand with no mirrored partner. 10 were re-rendered on version 6 before going out. `missing-lid` and
  `seabird-jet-lag` stayed that way. The other two, `everyday-breaking` and `real-roast`, are on version 1's balls.
- 7 Collage reels leave `side` out, found by walking the episodes' syntax trees. 6 of them have a right arm drawn with a
  left hand: `any-news`, `fluent`, `ill-get-this`, `regards-dad`, `sensor`, `thought-of-you`. `its-gone`'s arms are left
  arms, which is an unsaid side and not a wrong one.

19 reels in all. `any-news`, `fluent`, `ill-get-this`, `its-gone` and `regards-dad` are published, so they are rows of
the list, with `missing-lid` and `seabird-jet-lag`. `sensor` and `thought-of-you` are not published, so they now say
their sides, and their right arms get a right hand on their next build.

## Limits

- Rafa is a named gap: `rafa._hand` puts his thumb on the arm's side through the contract, but his four fingers are one
  row on both hands, 0.5 off centre, so the right hand is not an exact mirror of the left. He is approved, so he stays
  as drawn until the operator says otherwise. `anatomy_parts.NOT_MIRRORED` lists him and a test pins it.
- `side=` is a declaration. A caller who says the wrong side of a Collage arm is not caught: an arm drawn by coordinates
  does not know whose shoulder it left.
- A single-drawing prop carries its side in the table, but a caller can still place it on the other arm. The table
  stops it being undeclared, and rule 2 (ADR 0145) asks whose arm it is on.
- A pilot is not built by `srstudio build` and leaves no record, so `episodes/publish_pilots.py` has nothing to read.
  Its build still refuses in `Episode.finish`.

## Alternatives rejected

- Eight checks, one per style: the fault this replaces, as each style's rule reads differently.
- Reading a hand's side from the frame: Bento's hands on his heart and face sit on the axis, and a Collage figure is
  placed after its arm is drawn.
- Refusing at the draw site: old versions must stay drawable for specimens, pins and the catalog.
- Grandfathering by date or by whatever is in the manifest: a named row can be read and argued with, and a date cannot.
- A `None` default for `side`: `None` is refused as a bad side by an existing test, and is what a caller's bug looks
  like. A private sentinel marks a side not said.
