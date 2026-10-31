---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0071: Vera's and Gus's heads move on the speech, as the default of version 2 of the News kit

- Status: proposed; the two rig records are approved by the operator's post, Slack 1793476335.465559, on 2026-10-31
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Amends [ADR 0060](0060-news-kit.md); reuses [ADR 0050](0050-organic-head-motion.md) and
  [ADR 0059](0059-older-cast-head-rigs.md)
- Back to the [library README](../../README.md)

## Context

The operator asked in Slack (1793475817.480469) that News Compiler videos adopt head movement from now on. The standing
rule that followed (1793475909.049829) defines the motion: it follows the speech and is not idle sway. A nod on the
stressed word, a tilt on a reaction, a turn toward the other anchor when they speak, a turn back to camera for the
deadpan line, and a small settle between lines. Shots stay held and the face stays readable at phone size. Every episode
built on `news_inked` gets it by default; version 1 of the kit stays still.

Facts that shaped the design:

- The anchors are not Toon `Look` characters, so `toon_head.figure` cannot draw them. `host_kit.perform` is the closest
  model: a plan from `head_motion`, nested groups, `toon_head._animate`.
- `head_motion.plan` knew glances on a timer and listening nods. It had no way to say "turned to that side of the frame
  from here to there".
- `perform` on version 2 hangs the head on one group whose anchor is 7 px from the chin, in front of a neck that runs 69
  px up behind the head, so the join is already a pivot.
- The registered parts `news-vera@2` and `news-gus@2` are approved and immutable, and their digests read `perform` with
  no plan.
- The seven delivered reels and the two pilots rebuild from these sources. The pilots call `news_kit.stage`.
- The body and the hands live in separate planes (`perform(over=)`), so a body that moved would have to take the arms
  with it, and a re-render would change more than the heads.
- Only `Pose.head` tilts a head today: nine beats of the seven reels, each by 3 degrees.

## Decision

1. **A rig is a head on its own groups over a body that never moves.** `news_inked._on_rig` nests the beat's tilt
   (`Pose.head`, as drawn before), the plan's turn, and the nod and roll, around the point the head sits on. All the hair,
   the ears and the skin are in the nod group. The nose, cheeks and freckles slide on a face group under the front hair,
   and the eyes, brows, glasses and mouths on a second one over it, so hair stays over the forehead and glasses stay on
   the eyes. The neck, collar, tie, jacket and hands are not in any moving group.
2. **Idle is off by the style, not by the drawing.** `VERA_MOTION` and `GUS_MOTION` in `news_head.py` set `idle_roll`,
   `idle_px`, `breath_px`, `breath_scale`, `avert`, `lean` and `follow` to 0, and `glance_every` to `GLANCE_OFF`, ten
   minutes, which no reel reaches. What is left is what the takes cause.
3. **Two styles.** Vera is small and rare: 5 px nods on 40 % of her accents, 1.4 s apart at least, on a stiff neck. Gus
   is big and late: 17 px nods on 90 %, no lead, on a loose spring, and a turn twice as wide that starts 0.4 s after the
   other starts (Vera's lag is 0.15 s). Both nods are the `^` signature: on Gus's close nods `~` jumped 14 px in a frame.
4. **`head_motion.plan` gains `facing`.** `(on, off, side)` spans added to the same `turn` and `face_x` channels, on the
   same springs, bounded by `limit`, refused when too short to finish, overlapping or not one side. With none, every plan
   is what it was.
5. **Who faces whom is `news_head.facing`.** By default from just after the other starts until just before the own next
   line, which goes to camera. Level eyes go to `side` for as long; any other eyes stay the beat's.
6. **A beat overrides it with typed data.** `Act(holds=(Hold("vera", "gus", until="close"),))` keeps Vera turned from that
   beat to the next beat with that event, across lines of her own; `Hold(.., "camera", ..)` keeps her on camera through
   the other's line. `until` names an event because a recording moves beats and never reorders them.
7. **Heads are the kit's default, gated by the record.** `news_inked.stage(acts)` draws heads and refuses a rig whose
   record is not approved, by name, as `toon_rigs.rig_of` does. `stage(acts, heads=False)` draws still, byte for byte.
8. **The rig is a second drawing.** `specimens.rig_digest` draws it through `news_inked.rig_specimen`, every eye, arm and
   mouth at the corners of its reach, and `parts.json` holds that digest. The versions' own digests do not change,
   because `vera` and `gus` draw no plan.
9. **The seam is proved with the Toon check.** `toon_head.open_seam`, `reach` and `_bounds` now read a `Seam` protocol
   that `HeadRig` and `AnchorRig` both satisfy. The cover is the top of the neck, which stays behind the skin at every
   corner of the style and at any tilt a `Pose` allows.

## Alternatives rejected

- **A rig for reels that opt in.** The first brief. The operator's rule makes it the kit's default.
- **The default regardless of the record.** A proposed rig would reach a reel, which `rig_of` refuses for Toon.
- **A proof mode that draws a proposed rig.** No longer needed once the operator's post approved the rigs, and one more
  way to reach a reel with an unapproved drawing.
- **The body leaning with the speech, as in `host_kit`.** It moves the jacket and the arms, breaks the picture-only
  re-render and fights a held shot.
- **Merging the plan's turn and the beat's tilt into one key track (`host_kit._merge`).** Two groups keep one kind of
  motion per group, and the tilt's keys stay what they were.
- **Hard-coding a turn as a `Pose.head`.** A tilt is not a turn: it does not move the face or the eyes, and a held turn
  would need a pose on every beat it crosses.
- **A hold ending at a second.** A new recording moves it.
- **A version 3.** No published reel moved these heads, so version 2 may gain its rig once (`parts.py`). Its drawing does
  not change.

## Version 3: the face stays on the skin

On 2026-10-31 Gus's blush was seen over his jaw line on a full turn. The face slides as one piece, and the old check
compared the eyes and the mouth with the skin's widest x at any height, so it never saw a mark low on the cheek, where
the head narrows, and never added the nod, which drops the face further toward that narrowing. Measured on the drawn
skin, Gus's blush has 12.1 px of room at rest and the rig took it 25.2 px past the contour at its limits; Vera's blush
went 4.8 px past.

Every limit that is not the face's stays the same: the turn, the nods, the seed and the timing. Only the slide and the
face's drop change: Vera `glance_face` 13 to 9 and `face_slide` 0.8 to 0.6, Gus `glance_face` 24 to 8 and `face_slide`
0.8 to 0.2. The rig digest draws those limits, so this is a new version, `news-vera@3` and `news-gus@3`, on arc4d3's
post Slack 1793483857.840949, with the same drawing digest as version 2. The test measures every mark at each of its
own heights with the slide and the nod at their limits together, and holds a floor on the slide so that the fix cannot
pass by removing the turn.

`stage` draws each anchor's latest approved version. `stage(acts, version=2)` keeps the old numbers, and a reel whose
delivered master is on them names it, so a rebuild draws what went out.

Version 3 does not put every mouth on the skin. The gape passes the chin at rest on the drawing itself, 9.9 px on Gus
and 16.7 px on Vera, and with the limits 28.0 px and 22.3 px; Vera's grin stays on the skin at rest and passes it by
6.4 px with the turn and the nod at their limits together. Gus's round mouth stays on the skin and covers the bottom of
his nose by 17.1 px at any turn, because the mouth and the nose slide together. No limit answers any of these, or none
that the approval covers: the fix is a change to a drawing. The test names the gape and the grin, so they stay visible.

The approval came before these were measured, and its condition was that every face mark stays inside at the limits.
arc4d3 decided on Slack 1793486162.509569: "Option 1: `news-gus@3` and `news-vera@3` stay approved, with the gape,
Vera's grin at both limits, and the round mouth over the nose recorded as open drawing defects. I looked at the frames:
the shout reads as a normal cartoon jaw-drop at phone size, and it's in the original drawings, not new." The open
defects of version 3 are therefore: the gape past the chin on both anchors, Vera's grin past the skin at both limits
(6.4 px and 4.8 px), and Gus's round mouth over the bottom of his nose. In the same post arc4d3 agreed to a redraw:
"Yes to v4: redraw the gape inside the chin and lift the round mouth clear of the nose."

## Version 4: the mouths fit the face

Between Gus's nose and his chin there are 63 px at rest, and the mouths of version 2 were drawn taller than that: the
gape 78 px, the round mouth 60 px with the open mouth 52 px starting above the nose. Version 4, `news-vera@4` and
`news-gus@4`, redraws those states and nothing else. The gape ends inside the chin with the face at the end of its drop, at -45 on
Gus and -43 on Vera, and it takes in width what it gives up in height: 114 px wide on Gus and 86 on Vera, against 97 and
68 for speech, so a shout still shows at least a quarter more mouth than a word. Gus's open mouth and his round mouth start at -91, clear of
his nose. Vera's grin ends 7 px higher, which keeps it on the skin at both limits. The rig is the one of version 3.

Two faults stay, named in the test: Gus's gape still covers the bottom of his nose, because lifting it clear leaves no
height to tell a shout from a word, and his `teeth` mouth touches the nose's ink by the width of its own line.

A specimen of version 4 draws every mouth state, in its drawing digest and in its rig digest, because the states it
changes are ones the specimens of versions 2 and 3 never showed. Those two keep their digests. A delivered reel names
`version=3` in its `stage` call, so that approving version 4 changes no rebuild of it.

arc4d3 approved both on Slack 1793489634.822829, by the operator's delegation of 2026-10-31: "*v4 mouths: approved* for
both anchors." and "New News episodes build on v4, including fake-mars when it clears. Approved reels stay on v3, as
agreed." So `stage` draws version 4 by default, and a delivered reel keeps its own `version=3`.

Rejected: redrawing the chin, a longer jaw or a lower chin line, which changes the head. Smaller limits, which cannot
help a mouth that is past the skin at rest.

Rejected: clamping the slide inside the reels and leaving the style alone. The digest would hold while the specimen
still showed the defect, which routes around the gate. Moving the cheeks less than the eyes: a change to how the face
is built, not to its limits, and more than this fix needs.

## Consequences

- A rebuild of a delivered News reel now draws moving heads. A reel that must stay as published needs `heads=False`.
- The cover of a re-rendered reel takes its backdrop from the moving picture, so its frame can differ in the heads.
- Turns toward a speaker show in two-shots and at the edges of a close-up: a close-up mostly shows who is speaking, and
  they face camera.
- `Hold` is on `Act`, which version 1 also uses and ignores.
- A change to either rig's drawing after approval is a new version of the anchor.
