---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0230: A controller held in both paws

- Status: proposed (2026-11-04). The drawings it adds, `toon-leo` and `toon-sam`, are proposed with their rigs, and
  the proof is at `generated/character-proofs/between-friends/index.html`
- Deciders: the operator; ordered by arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0047](0047-character-versions.md), [ADR 0052](0052-older-cast-version-2.md),
  [ADR 0059](0059-older-cast-head-rigs.md) and [ADR 0143](0143-bento-hands-are-a-pair.md)
- Back to the [library README](../../README.md)

## Context

The Between Friends pilot is a held two-shot of two friends on a couch, seen from the TV, each holding a game
controller for the whole film. Their faces carry the story, and their hands carry the game: thumbs on the sticks while
they play, a thumb on a button to pause, the controller sinking to the lap when the talk turns, lifted again when they
play on.

No shared Toon arm kind (`toon.ARMS`) holds anything in both hands. A limb track (`limbs`) draws a free arm over a
pose, one per side, with no shared object between the two hands, and nothing in it knows that two thumbs on one
controller lie toward each other. The hands rule (ADR 0142, ADR 0143) asks that the right hand be the mirror of the
left, and that with the palms toward the camera both thumbs point in.

## Decision

`srstudio.toon_gamepad` adds a controller held in both paws as poses of a critter's own.

- `Player` is a `toon_critters.Critter` in a top. Its own arm kinds are the four `GRIPS`: `pad` (both thumbs on the
  sticks), `pad-press` (the right thumb on a button), `pad-lap` (lowered, thumbs off) and `pad-up` (lifted). Each is a
  typed `Hold`: the controller's centre, the elbows, and where each thumb lies, which `Hold` checks against
  `THUMB_PLACES` when it is built.
- They are gestures in the `toon_cast.Posing` sense, the way Bento's are: `gesture(arms)` returns the drawing for a
  grip, `None` for a shared kind, and refuses any other name. So a grip works wherever a pose does: through the head rig
  (`toon_head.figure`), in the specimens, and in the hands the build records (`pose_hands` records both arms).
- The paws are a pair. `GRIP` is one drawing, made for the frame's left arm, palm on, its thumb toward the frame's
  right. The frame's right paw is that drawing reflected, because `GRIP.mirrored` says so for the hand its `Arm` gives:
  no caller chooses the mirror. Both thumbs lie over the controller's top edge and point in.
- The controller is generic: a rounded body with two grips, a pale bumper and two stick caps, in its own greys. No
  brand's shape, button or colour.
- `toon_friends` draws Leo and Sam as players. Their builders draw through their rigs held still
  (`HeadPlan.still()`), as Bento's do, so a pose may name a grip wherever it names an arm, and a limb track is refused.
- `specimens.OWN_ARMS` puts the grips in each drawing's digest, and `specimens.OWN_RIG_ARMS` puts them in each rig's
  digest, so a change to a hold moves both. A rig not listed there draws what it drew before, so no approved rig
  digest moves.
- Both are version 1, proposed, with proposed rigs (ADR 0047). `toon_rigs.rig_of` refuses them, and no reel can draw
  them until the operator approves.

Their chins close below the hood and the collar (`open_chin=False`) on a quarter circle off each neck join
(`toon_friends._rounded_chin`). A chin that turns off a join at a right angle folds the shade band over itself and
leaves a fleck of bare coat at the jaw.

## Alternatives rejected

- A limb track per arm with a controller drawn between them: two free arms do not share a held object, nothing ties
  the thumbs to the controller, and the tracks draw over the face's arms in a separate pass.
- New shared arm kinds in `toon.ARMS`: every Toon character would have to draw a controller, and every approved
  specimen would change its digest.
- Thumbless mitts round the grips: a controller is played with the thumbs, so the thumbs carry the action, and a
  thumbless hand cannot show a thumb moving to a button.
- Two drawn paws, one per side: two drawings to keep alike, the fault ADR 0143 fixed.
- Adding the grips to `specimens._rigged` for every rig in `OWN_ARMS`: Bento's approved version 2 rig would change its
  digest.

## Consequences

- `toon.parse_poses` still holds to `toon.ARMS`, so `toon_pair.figure` and the sketch pipeline cannot pass a grip yet.
  A reel that needs them on a sketch needs that parser to accept a drawing's own kinds. Until then a reel draws them
  through `toon_head.figure` directly.
- A shared pose (`desk`, `crossed`, …) draws the critter's ordinary mitt in the sleeve's colours.
