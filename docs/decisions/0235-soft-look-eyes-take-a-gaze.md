---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0235: Soft "look" eyes take a gaze

- Status: proposed (2026-11-04)
- Deciders: the operator; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0047](0047-character-versions.md)
- Back to the [library README](../../README.md)

## Context

The Soft rig (`srstudio.blob`: Pip, Bo, Juno, Remy) draws its `"look"` eyes with both pupils 8 units to the left of
each eye. The face is a group that follows the head but is never mirrored, so a cue with `flip=True` turns the body
and leaves the pupils on screen left. A figure told to look at someone on its right looks away from them, and the
cue had no way to say otherwise.

Reels already published use `"look"` with `flip=True` (`hang_out.py`, `whats_new.py` in srstudio-episodes). Their
drawing is frozen: a change to the rig must leave every existing cue drawing the same bytes.

## Decision

`Cue` gains `gaze`, one of `blob.GAZES = ("left", "right")`, defaulting to `"left"`. It is the screen side the
`"look"` pupils point to; `flip` does not change it. A `"right"` gaze draws its eyes in a group of its own,
`<id>-eyes-look-right`; a `"left"` gaze keeps the old group, `<id>-eyes-look`, and the old shapes. The rig refuses a
gaze it does not have, and a non-default gaze on eyes other than `"look"`, rather than ignore it. The Soft contract
lists `gaze` among the cue's fields and `gazes` among the vocabularies.

## Consequences

- A cue that names no gaze draws exactly as before. `tests/test_blob_gaze.py` holds the digest of a performance with
  every eye shape and `"look"` facing both ways, on all four rigs, taken on develop `0d120676` before the field
  existed; hang-out and whats-new built with the library before and after the change give byte-identical scenes.
- A new reel that wants a figure to look right sets `gaze="right"` on that cue.
- `Cue.gaze` is the last field, so positional `Cue(...)` calls keep their meaning.

## Rejected alternatives

- **"look" follows the facing** (pupils right when `flip=True`). It is the natural reading of the eye state, but it
  redraws every published cue that combines `"look"` with `flip=True`.
- **A new eye kind, `"look-right"`.** `blob.EYES` is the vocabulary the Soft specimens walk, so a seventh eye kind
  would change the specimen, and with it the approved digest, of every Soft character (ADR 0047).
