---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0174: A figure draws one pair of hands, counted across its layers

- Status: accepted (2026-11-02), ordered by arc4d3 (Slack ts 1793592932.697149); written by Claude Opus 5.5 in Claude
  Code
- Amends rule 2 of [ADR 0148](0148-anatomy-is-a-build-error.md), and reads a hand on the frame as d26630ed and ADR 0148
  define it
- Back to the [library README](../../README.md)

## Context

arc4d3 ruled that Bruno's Wow in `it-autoplayed` is an anatomy fault: he raises both arms while his body drawing keeps
its two paws resting on his belly, so four hands are drawn. The sofa's back covers the belly in the master, so two show.
A higher seat would show all four. The ruling: rule 2 counts the hands per figure across pose layers, and the build
fails even when only a seat would expose them.

ADR 0148's `arm-third` could not see this. It counted only the `Limb`s a Collage `arm` and `reach` recorded, never a
pose's own hands, and a Toon swung arm recorded nothing. Commit d26630ed made it count a hand only where it can be seen,
which is right for two scene hands on one arm and wrong for this ruling, where the hidden paws are the fault.

## Decision

- A pose records the hands it draws. `toon_cast.figure` and `toon_head` record one `Limb` per arm the pose draws, on the
  pose's group, plus one per limb track. A Collage pose records the hands its arms draw: none on a toilet, the
  screen-right one for `free`, the screen-left one for `free-right`, both otherwise. `anatomy.json` now keys a limb by
  node and side, so one drawing holds two hands.
- A swung Toon arm ends in a hand, so `toon_bed.swung_arm` and `toon_pair.reach` draw through
  `anatomy_ledger.loose_hand`. Inside `with anatomy_ledger.on_arm(owner, side):` the arm records the hand on that
  character. Outside one, the build is refused as `hand-no-arm`. `on_arm` changes no drawing.
- `hand-count`, on the frames, at the build and at first delivery. It counts each figure's hands, where a figure is one
  character call in `figures.json`. A hand recorded on a body drawing belongs to that figure. A hand on no body drawing,
  such as a swung arm, belongs to the figure of its character nearest it in the scene tree. A crowd of one character is
  therefore so many figures, each with its own pair. A hand counts when it is drawn: gating and opacity hide it, but a
  set, another figure or the frame's edge does not. A figure with more than one pair is refused. The one exception is a
  figure none of whose body drawings is seen, such as one wholly behind an insert, which counts only the hands seen.
- A node is seen by its own pixels, not its bounding box. Some of what the node draws must lie inside the frame and not
  under a solid shape drawn in front. Before this, an uncovered empty corner of a figure's box counted as seen.
- `arm-third` keeps reading the hands a scene draws, not a pose's own. A pose hand and a scene hand are one figure's
  pair whatever side an unsaid arm defaults to, and a figure over its pair is said once, as `hand-count`.
- `bust-open`, `hand-no-side` and `hand-unpaired` are unchanged.

## The two readings

d26630ed asks whether a hand is on the frame, and that stays the reading for `arm-third` and for a figure with no body in
view. The ruling asks how many hands one figure is drawn with, and that is `hand-count`'s reading. The case that tells
them apart is `thought-of-you` at 3.5 s. Gary's bed-shot arm, c468, holds the phone behind the insert, and the insert's
POV hand is that same hand seen from his eyes. His bed pose is wholly behind the insert by its pixels, so his figure
counts only the hand that is seen: one, and no fault. c468 is not a third hand.

## What it finds

Every project in `generated/episodes` that has a script on this branch was rebuilt on a copy (202 built) and measured
on the engine's frames every 0.5 s:

| Reel | Figure | Where (hands) | Published |
|---|---|---|---|
| `home-anyway` | rabbit | 5 s, 7 s, 13 s, 22.5–24.5 s (3) | yes |
| `ill-get-this` | gary | 22.5–23.95 s (4) | yes |
| `ill-get-this` | rosa | 20.5 s (3) | yes |
| `it-autoplayed` | bear | 4.5 s (4); 12–12.5 s, 14.5–15.5 s (3) | yes |
| `it-autoplayed` | rabbit | 15–15.5 s (4); 12–12.5 s, 23–25.25 s (3) | yes |
| `its-gone` | rosa | 17.5–20.8 s (3) | yes |
| `nine-alarms` | bear | 22.5–24 s (4); 5–8 s (3) | yes |
| `nine-alarms` | rabbit | 4 s, 8.5–11.5 s (3) | yes |
| `regards-dad` | gary | 11.5–17 s (3) | yes |
| `texts-back` | dog | 4.5–5.5 s (4); 0–3 s and through to 24.47 s (3) | yes |
| `texts-back` | rabbit | 0–1 s, 13–14 s, 21.5–22 s (3) | yes |
| `sensor` | jun | 17–20.05 s (3) | no, held |

Each is a body drawing with its pair plus one or two arms the scene draws for the same character. The pair is hidden by
a sofa, a counter, a desk or the held object, as in Bruno's Wow. On develop's reading, `arm-third` flagged only
`ill-get-this` gary at 22.5–23.95 s, which is now this table's four-hand row. `thought-of-you` and the `someone-else`
call centre are clean.

The published reels are frozen. Rebuilding one with an engine now ends `srstudio build` with exit 1 until a row of
`assets/anatomy_published.json` excuses it: rule `hand-count`, part the figure's name, one per published row above. No
row is added here. `sensor` is unpublished and is fixed in its scene, by `omit_arms` or by a pose with the hands it
needs, before it is delivered.

`it-autoplayed`, `texts-back`, `nine-alarms` and `home-anyway` gained `on_arm` declarations only. Their scenes rebuild
byte for byte as the tree before the change builds them.

## Limits

- A prop's hand inside `on_arm` (a phone or clipboard with `hand=`) records no node, so it is not counted.
- Toon pose sides are recorded as drawn, before any mirror. The count does not use sides.
- Only Toon and Collage poses, Toon swung arms and Collage `arm` and `reach` record hands. Other styles' figures record
  none, so the count does not see them.
- Pilots are not built by `srstudio build`, and 55 projects with no script on this branch, plus 5 whose build fails
  another gate, were not measured.
- The frames are `framegraph`'s, so layers and effects are not read, as in ADR 0073.

## Alternatives rejected

- Counting only the hands seen, d26630ed's reading, for the count too: that reading passes Bruno's Wow, the fault ruled.
- Counting per character name: a crowd of one character becomes one figure with many hands.
- Counting pose hands in `arm-third`: an arm that leaves its side unsaid defaults to the side of the pose's own hand,
  and every such pair becomes a false third.
- A POV marker on the insert's arm in `thought-of-you`: `view=POV` turns the thumb over, which changes a published
  picture.
