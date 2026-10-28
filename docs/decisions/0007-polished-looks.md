---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0007: Polish as look options, and two polished Soft characters

- Status: accepted and implemented, 2026-10-28 (`blob.Look.shade`, `gloss`, `catchlights`, `lashes`,
  `blob.juno`, `blob.remy`, `tests/test_soft.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The Soft cast was Pip and Bo: one rig ([ADR 0005](0005-audio-call-and-looks.md)) drawn in flat fills, with
pupils as plain ink dots. The operator asked for two more characters, more polished than the first two.
Polish here means light: a shaded side, a highlight, light in the eyes, and accessories with their own sheen.

## Decision

1. **Polish is part of a look, and off by default.** `Look` gains four options:
   - `shade`: a colour for the crescent of the head that a disc moved toward the light (upper left, `LIGHT`) leaves
     uncovered. It is drawn over the head's fill and under the hair, so the hair and headset sit on it.
   - `gloss`: a highlight following the head's curve on the lit side, with a dot after it.
   - `catchlights`: the same light in every pupil, a large spot up and left and a fleck below.
   - `lashes`: two flicks at the outer corner of every eye shape: open, look, wide, happy, squint and closed.

   `shade` is checked like the other colours. `_crescent` refuses a lit disc that has not moved or has moved by
   the diameter or more, because there would be no crescent or no head left.
2. **Pip and Bo do not change.** Their looks leave the options off, so they draw exactly the shapes they drew
   before. Every episode scene document (camera-off, focus-mode, five-years, the-router, mushroom-training)
   was rebuilt and compared byte for byte with the build before the change.
3. **Juno and Remy are the rig in two polished looks.**
   - `juno` is the colleague who already did the reading. Apricot body with a shade. Auburn bun, wound in two
     strands with a sheen. Scalloped bangs, and a coral scrunchie where the bun meets the crown. Freckles over
     the blush, catch-lights and lashes.
   - `remy` is IT support. Lavender body with a shade and a gloss. A three-lock tuft that curls at the tips. A
     headset: padded band, ear cups with an amber status light, and a mic boom to beside the mouth. Catch-lights.

   Both are registered Soft characters, and every pose and cue works for them as it does for Pip.

## Rejected alternatives

- **Shade the whole body.** The limbs are hold-keyed outline paths merged under one outline. A shaded side on them
  needs a clip or a second keyed path per limb, and an unclipped shade path would cover the outline. Shading the
  head, where the eye goes, gives most of the effect for one static path.
- **Turn the polish on for Pip and Bo.** It would change two published episodes. The options exist, so an
  episode can opt in when it is rebuilt.
- **Draw lashes as a feature.** Features are one static drawing over the face, but the eyes change shape with
  every cue. Lashes drawn with each eye kind follow the eye.

## Consequences

- A new character chooses its polish in its look; nothing in the rig has to change for it.
- A polished head costs one path for the shade and two shapes for the gloss. Catch-lights cost two ellipses for
  each eye with a pupil.
