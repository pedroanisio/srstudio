---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0239: Soft figures draw a pair of hands

- Status: proposed (2026-11-04)
- Deciders: arc4d3 (the drawing), the operator; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0047](0047-character-versions.md), [ADR 0147](0147-hand-chirality-is-a-build-error.md),
  [ADR 0148](0148-anatomy-is-a-build-error.md) and [ADR 0174](0174-a-figure-draws-one-pair-of-hands.md)
- Back to the [library README](../../README.md)

## Context

The Soft rig (`srstudio.blob`: Pip, Bo, Juno, Remy) ends each arm in a rounded cap. Juno & Pip are the leads of
the relaunched Okayville series and act in medium two-shots, so a shrug or a "whoa" is carried by the arms alone, and a
prop held through `blob.held` or `soft_odds.in_hand` floats at the arm's tip. arc4d3 asked for hands drawn as
mirrored pairs (L21).

Approved Soft drawings are frozen. Published reels call `blob.pip`, `blob.juno` and the rest, and the approved digest
of each character is taken from the poses it walked when it was approved. A hand on every Soft figure would redraw
every reel already built.

## Decision

- **One drawing, mirrored.** A hand is a Soft mitten: an oval palm and an oval thumb, filled in the look's body colour
  and inked like the limbs. `blob.MITTEN` is that one drawing, registered with the anatomy contract as the frame's
  left hand, palm to camera (`Drawing("soft-mitten", Side.LEFT, Facing.PALM)`).
  - Every other hand is that drawing reflected wherever `MITTEN.mirrored(Arm(side).hand(facing))` says it is, so the
    right hand is always the left one's mirror, and the thumb follows ADR 0147.
- **Placement.**
  - The mitten is laid along the arm's end tangent, its wrist on the arm's tip.
  - The arm's frame side comes from the shoulders (`blob.arm_sides`), so it holds through a flip.
  - It faces the palm out for the arms named in `blob.PALMS[pose]` and the back otherwise (`blob.facing`).
  - It is keyed on every drawing, like the limbs, and drawn in the same pass as its arm: behind the body while the arm
    is behind it, and in the arm's front group, over its trace, while the arm is in front.
- **Opt-in, as a new version.**
  - `Look.hands` defaults to `False`, and no existing look sets it.
  - The handed looks are `PIP_HANDS`, `BO_HANDS` and `JUNO_HANDS`, registered as the characters `pip@2`, `bo@2` and
    `juno@2`, each version 2 in `assets/parts.json` with status `proposed` and no approval.
  - Soft characters become routed (`parts.CALLED`). A build calls the version it wants by name; nothing reads a pin.
- **Recorded.** A handed figure records its pair with `anatomy_ledger.pose_hands`, so the hand count of ADR 0174
  sees it.
- **Gestures.** Three seated poses act with the hands: `shrug` (palms up either side of the body), `explain` (the
  near palm offered by the chest, the far hand on the thigh as in `lounge`) and `whoa` (both palms out at the shoulders).
  - They join `POSES` and `POSES_SINCE_APPROVAL`, so no approved specimen walks them.
  - Each near arm drops its elbow and lifts its forearm by the chest. Every hand stays inside half the gap between two
    seated marks of a medium two-shot (Juno & Pip's flat: 520 px at scale 1.6), so a figure never reaches into its
    partner.
  - No gesture arm bends tighter than half its inked width, held or at any point of its blend from `lounge` or from
    another gesture, so no outline folds over itself at the elbow while it moves.

## Consequences

- Nothing published moves. `tests/test_blob_hands.py` holds the digests of all four rigs performing every pose they
  had before this change, with a held prop and a prop in hand, taken on `integ/sdk-nov04` `a0828147`. The drawing
  stays byte-identical.
- A reel that wants hands calls `registry.get("character", "pip@2")` (or `blob.pip_2`), and so on. Until arc4d3
  approves version 2, it is never the default, and a published or approved reel does not use it.
- Held props still ride between the tips (`blob.held`) or at one tip (`soft_odds.in_hand`). The hands now sit around
  them; the tests check that a prop held in `phone-a`, `phone-b` and `sit-show` lands between the two hands.
- Remy has no handed version; one is added the same way when a reel needs it.
- The older `phone-a` and `phone-b` poses still fold at the elbow, held and on the way into them. They are drawn in
  published reels, so they are left as they are.
- `sit` (the typing pose) reaches both forearms forward. In a two-shot with hands, its hands meet the partner's, so
  a handed pair rests in `lounge`, as the flat's marks do.

## Rejected alternatives

- **`hands=True` as a call option on the existing characters.** It would change the look under an approved version
  without a new digest, so no record would say which drawing a reel used.
- **Routing Soft versions through pins.** It would need every Soft build to read a pin. Calling `pip@2` by name
  records the version in the build itself.
- **Hands as props drawn through `soft_odds.in_hand`.** A prop is not part of the figure. Hand count (ADR 0174) and
  chirality (ADR 0147) would not see it, and a pair would not be mirrored by construction.
- **Gestures added to the approved specimen.** New poses in the walked set would change the approved digest of every
  Soft character (ADR 0047).
