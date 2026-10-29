---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0012: Stick figures with looks, standing poses, a call screen, and caption outlines the check can measure

- Status: accepted and implemented, 2026-10-28 (`stick.rig`, `stick.Look`, `stick.HAIR`, `stick.STANDING`,
  `stick.call`, `stick.Tile`, `stick.Mail`, `stick.captions(outline=)`, `tests/test_stick.py`,
  `episodes/screen_share.py`); amends [ADR 0009](0009-stick-rig.md)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator asked to improve the library and enhance the Stick style. Rendering *Screen Share* (R2) as ADR 0009
left it showed the gaps:

- the rig drew one person: every figure had Dev's cowlick, so the boss could only be a voice;
- it could only sit, at one place and size;
- the joke about a shared screen had no screen;
- every encode reported 14 `LEG-CONTRAST` warnings on the captions. The engine measures a text layer by the pixels
  it changes (`contrast_of_coverage` in `sr-gpu`), and a white caption stroked in ink changes white and ink pixels
  alike, so their mix was measured against the wall. The captions were legible; the measurement could not tell.
- the close shots centred on Dev's head and cut out the laptop he looks at;
- three lines of the hook at the episode's size overflowed the card's text box by 6 px (`TXT-FIT`).

## Decision

1. **`seated` becomes `rig`**, the `stick-rig` part, with a `Look`: a hairstyle from `HAIR` (cowlick, spiky,
   side-part, bun, bald), glasses, and a tie colour drawn along the torso of every pose. `check_look` refuses an
   unknown hair, non-boolean glasses and a tie that is not a hex colour. The default look, `PLAIN`, draws exactly
   what ADR 0009's rig drew.
2. **Placement.** `at`, `scale` and `flip` transform the figure's group about the frame origin, so pose sets
   drawn in frame pixels can stand anywhere and face either way; `scale` must be positive.
3. **`STANDING`** adds six poses on the room's floor (`stand`, `wave`, `point`, `hands-hips`, `shrug`, `lean-in`).
4. **`stick-call`** (`stick.call`) draws a video call filling the frame: a shared inbox (`Mail` rows, unread in
   bold with a dot, one row optionally marked) above the caption line, the participants' tiles (`Tile`: name, look,
   face; the speaker ringed) below it, and the call's buttons. It refuses 0 or more than 4 tiles, 0 or more than 7
   mails, blank or repeated names, a mail without sender or subject, a speaker who is not a tile and a marked row
   out of range.
5. **Caption outlines.** `captions(outline=)` takes `"stroke"` (the package's one stroked layer, kept for the
   fidelity port), `"layer"` (the outline as its own ink text layer under unstroked white text: pixel-identical,
   measured white against ink) or `"none"` (white alone, for a dark backdrop such as the call, where an ink outline
   cannot contrast and the white needs none).
6. **The card's text box** is 16 px shorter than the card instead of 30 px, centred where it was, so three lines
   fit at 62 px.

*Screen Share* uses all of it: takes 01 and 03 are the call, with the camera pushing in on the inbox whose first row
is about Dev; on Friday the boss stands in the room, mirrored to face Dev, bald, in glasses and a red tie; close
shots centre 100 px right of Dev's head. Its encode reports no contrast warning.

## Rejected alternatives

- **Accepting the contrast warnings as a false positive.** Rejected: the engine has no way to mark a text layer as
  decorative, and a check that always warns hides the warning that matters. With the outline split, the one
  warning left was a real defect: a cue rounded to 6.054 s was taken for the call's by a time comparison and lost
  its outline over the wall. The build now sorts cues by their take, not their time.
- **A background box behind the captions.** Rejected because the style's captions are outlined text; a box
  changes the look.
- **A second figure function for standing.** Rejected because a standing figure is the same joints with other
  values; one rig with pose sets keeps faces, looks, mouths and blinks in one place.
- **Mirroring by negative `scale`.** Rejected because `scale` sizes the figure and is checked to be positive;
  `flip` says what it means.
- **The call as a laptop-screen texture inside the room.** Rejected because the laptop faces away from the
  camera, and a full-frame insert reads at phone size.

## Consequences

- A Stick episode can cast several people, standing or seated, and cut to a call; only the figure's facing is
  profile, so a figure seen from the front needs another pose set.
- `srstudio catalog --style stick` lists nine parts; the catalog shows the boss and the call screen from R2.
- Callers of `stick.seated` call `stick.rig`; the episode and tests in this repository do.
