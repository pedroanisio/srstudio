---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0009: A drawn Stick figure that talks, a push-in camera and a font hook card

- Status: accepted and implemented, 2026-10-28 (`stick.seated`, `stick.camera`, `stick.card`, `stick.RigPose`,
  `stick.Face`, `stick.RigKey`, `stick.SEATED`, `stick.check_keys`, `tests/test_stick.py`,
  `episodes/screen_share.py`, `episodes/screen_share_audio.py`, `tests/test_screen_share.py`)
- Amended by [ADR 0012](0012-stick-looks-and-call.md): `seated` is now `rig`, with looks, placement and standing
  poses
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The operator asked for a stick-figure office reel to be recreated with the engine, voiced with ElevenLabs, and its
style added to the library. The reel's drawings, jokes and lines belong to its author, so the episode made from it is
an original one, *Screen Share* (R2): new character, new script, the same style family as ADR 0006.

ADR 0006 left the Stick style unable to do that. Its figure is traced: each pose is a set of plates from the
reference, so a new episode needs new tracing, and the style is `silent=True` because no figure has a mouth. The hook
is traced lettering, so a new hook needs new glyph plates. There is no camera move.

## Decision

1. **`stick-rig`, a drawn figure.** `stick.seated` draws a seated stick figure from joints, not plates: a `RigPose`
   (head, neck, hip, and far/near knees, feet, elbows and hands) in ink limbs (`LIMB`, `LIMB_FAR`), and a round
   `SKIN` head of `HEAD_R` with a cowlick. `SEATED` holds six poses that fit the `stick-room` chair and desk
   (`type-a`, `type-b`, `lean`, `back`, `turn`, `stretch`); an episode can pass its own.
2. **A performance is keys, and the keys are checked.** A `RigKey` is a start, a pose name and a `Face` (eyes, brows,
   closed mouth, look). `check_keys` raises `StickDataError` unless the first key is at 0, keys are in time order and
   before the end, every pose and face value is known and the look is within −1..1. Bodies are gated per key, so a
   seek is exact.
3. **The mouth comes from the voice.** With `phones`, the mouth runs `soundtrack.phoneme_states` on the Ink mouth
   model (`INK_MOUTH`: closed, open, round, teeth, shout); between words it closes into the current face's mouth.
   The figure can lip-sync, so a Stick episode is no longer silent by necessity; `STICK` keeps `silent=True` as its
   default for the traced port.
4. **`stick.camera`** anchors a group on a focus point and either holds a zoom or pushes in with sine-in-out keys
   over a span. It refuses a zoom below 1 and a negative push.
5. **`stick-card`** is the hook in the caption font: ink Inter text balanced over up to three lines on a rounded
   white card (`CARD`). It raises without a font and on empty text. A new hook is a string, not a tracing.
6. **The episode is verified like the others.** `screen_share_audio.py` voices each line with ElevenLabs (Will for
   Dev, Eric for the boss) and keeps a take only after speech-to-text matches the script; `screen_share.py` refuses a
   caption page wider than the frame, measured with the font.

## Rejected alternatives

- **Tracing the reel's figure and lettering.** Rejected: it copies a third party's drawings; a drawn rig is the
  style's technique without the author's art.
- **Extending `stick-figure` with mouth plates.** Rejected because every new expression would need new tracing; a
  rig with a face model draws any face from four values.
- **A Soft-style blob rig recoloured.** Rejected: Stick figures are ink limbs with a round head; a blob reads as
  Soft.
- **Reusing `stick-hook` for the hook.** Rejected because it draws glyph plates; any new text needs the font.

## Consequences

- A new Stick episode needs a script and keys; the figure, the room, the camera, the hook and the captions come with
  the library.
- `srstudio catalog --style stick` lists eight parts; the catalog shows Dev and the hook card from *Screen Share*.
- Only the seated poses exist; a standing or walking figure needs new `RigPose` sets.
