---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0062: Bento, the operator's capybara, as a Toon character

- Status: accepted (2026-10-31). The operator approved him from his clips: "bento is approved". Implemented: `srstudio.toon_bento`, the `toon-bento` version record with its rig record
  in `parts.json`, `pose_tilt`, `tilt_reach` and `face_slide` on `HeadRig`, `Ramp` and `Posing` in `toon_cast`;
  `tests/test_toon_bento.py`, `tests/test_toon_head.py`.
- Deciders: the operator (pedroanisio), who authored the character; port drafted by Claude Opus 5.5 in Claude Code
- Extends [ADR 0020](0020-toon-lip-synced-cast.md), [ADR 0047](0047-character-versions.md) and
  [ADR 0050](0050-organic-head-motion.md)
- Back to the [library README](../../README.md)

## Context

The operator authored Bento: a capybara in a tailored blazer, with a broad muzzle, caramel fur, small rounded ears,
front teeth and tiny paws. He brought a pack of plates with 36 moods, 12 eye states and 9 gestures, and asked for the
character in the catalog as a Toon character that can move and talk. The drawing is his, so the port follows it closely
and any difference is named here.

A catalog drawing here has a digest and is drawn by this library. Plates and scripts copied in would have neither, and
they would bring the pack's show branding and lettering with them. So the geometry is ported and the rest is left out.

Two things in his drawing do not fit the rig as it stood. His head is one big form with a muzzle laid over it, and most
of the moods tilt that whole head. His fur and blazer are soft gradients, where the Toon cast is flat fills.

## Decision

1. **`toon-bento` version 1 is drawn through `Canvas` and `brush`.** His drawing's coordinates map onto Toon reference
   pixels at 0.85, so the head sits where a Toon head sits. Every shape is a brush shape, and the digest covers it.
2. **The moods, eye states and gestures are typed data.** A `Mood` holds brows, lids, gaze, mouth, tilt, pupil, marks and
   its gesture. `mood` and `pose_of` refuse an unknown name. English names only.
3. **The head goes over the blazer, with its own inked chin.** His drawing has the head in front of the blazer: the
   chin at y 700 lies 35 reference pixels below the blazer's top line at y 665. The blazer's top line is the rig's
   `cover`. Measured at the rig's bounds, which hold the widest mood tilt, `open_seam` is empty, still empty with the
   head lifted 4 pixels, and opens at 6.
4. **The muzzle rides in the face group.** The creases under his eyes run along the muzzle's top, so the eyes and the
   muzzle have to move together.
5. **His face slides less on a nod: `HeadRig.face_slide`, 0.2 for him.** At the shared 0.8 the muzzle pushed 8.8 pixels
   past the head line at the deepest nod. His drawing already laps it 3.57 at rest, so `MUZZLE_LAP` allows 6.
6. **A mood's tilt is held by the rig, not by the head's motion plan: `HeadRig.pose_tilt`, in its own group between the
   turn and the nod.** Each pose keeps the old tilt at its start and reaches its own `TILT_EASE` later, on a spring. A
   spring runs from one key towards the next, so a single key at each start would lean into the pose after. `tilt_reach`
   adds the widest tilt to the rig's bounds, so the seam check covers it.
7. **Gradients are a named fill: `toon_cast.Ramp`.** A plain colour string still draws as it did. `Ramp` subclasses
   `str`, so a layer stays a `(shape, colour)` pair.
8. **`toon_cast.Posing` lets a drawing bring its own arms and its own shut eyes.** His gestures are whole drawn poses, and
   the shared blink would cover a mood whose eyes are already shut.
9. **The shared vocabulary works on him, mapped to his nearest drawing.** A sketch can cast him with the kinds it
   already knows. His moods by name are for scripts, through `pose_of`. A shared arm leaves from his own shoulder,
   because the cast's shoulders stand clear of his blazer and drew a hump above it.
10. **Limb tracks are refused by name.** His gestures are not rigged limbs.
11. **`bento()`, the flat registered drawing, is the rig standing still.** There is one drawing of him, and the digest
    covers it.
12. **No reel names him yet.** He and his rig are approved, so a reel may draw him; News keeps its own anchors unless the
    operator says otherwise. Published reels change by nothing: every hook is off by default.

## Where the port differs from the operator's drawing

- Drop shadows are flat, with no blur.
- Sleeves in the shared poses are even bands. His own gestures keep their drawn sleeves.
- Shapes clipped in his drawing are cut by columns, which `_meet` does, because a brush shape has no clip.
- The hearts eye comes from the shared drawing, because his pack has none.
- The tablet's screen is blank, ruled and unlabelled.
- Low gestures sit behind a Toon desk, whose top is at y 801. `CENTRED` frames him whole.
- The muzzle's outline has a notch of about 3 pixels at full frame at its top left corner, where the stroke's two ends
  meet. Starting the stroke elsewhere would run the spline across his real corners, which is worse.
- The newsroom set, the review boards, the show branding, the Portuguese labels and all lettering are left out.

## Alternatives rejected

- **The blazer over the head, like a ruff.** That would cut 35 reference pixels off the chin he drew.
- **An open chin, as for the redrawn six.** His head has an inked line all the way round, so that would change his
  drawing to suit the rig.
- **The muzzle in the skull group.** The eyes would slide over a fixed muzzle, and the creases under them would come
  apart from it.
- **Mood tilts as head motion keys.** A plan is built from speech, so the tilts would be lost in any shot with no line,
  and the seam check would not see them.
- **Vendoring the plates.** They would have no digest and would carry what this port drops.
