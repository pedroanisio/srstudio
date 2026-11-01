---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0079: A key line or hook card may not repeat the spoken caption, and first delivery refuses one that does

- Status: proposed
- Deciders: the orchestrator's ruling on the blind review of batch A, implementation drafted by Claude Opus 5.5 in Claude
  Code
- Back to the [library README](../../README.md)

## Context

A full-size review found the same words on screen twice at once: "Lost the whole left side." in a pale pill at the top of
`slept-wrong` and again in the caption at the bottom. `toon_house.key_line` and `stick.card` are drawn on top of the
picture. Each reel gives them their words and their window, and nothing compared either with the captions. Six reels of
the batch carried it in full and one in part.

The ruling separates two things that print alike:

- Text inside the picture that a character reads or holds up (a phone message, a sign, a chart, a card, a button) may
  match the caption. That is a caption of a thing being read, and it passes.
- An overlay added on top of the picture that repeats the spoken caption is the defect.

Facts that shaped the design:

- A built scene does not keep the ids a helper gave its groups: they are anonymized (`n123`), so `cv.uid("key-line")`
  cannot be found again.
- Both overlays have a fixed drawing. The hook card is a white rectangle with its text layer at a fixed offset,
  `stick.CARD`. The key line is a rectangle of `toon_house.KEY_LINE_BG` at `KEY_LINE_TOP`.
- `stick.card` belongs to an approved part. A new id or attribute on it changes the part's digest.
- A delivery already refuses reels through `releases.doubled_captions`, a scene and subtitle check that needs no engine.

## Decision

`srstudio.overlay_gate` reads a reel's scene and subtitles and refuses a first delivery when a key line or hook card shows
the words of a live cue for longer than `craft.DOUBLED`.

- An overlay is recognised by the drawing that made it, not by its words, so text inside the picture is never read.
- Its time window comes from its own and its ancestors' `start`/`end`, opacity and visibility keys, local time bases, and
  the sequence shifts that `craft` already computes.
- Two lines match when they are equal, when the shorter (of two words or more) sits whole inside the longer, or when
  they share a run of three words. A single word only matches itself.
- A reel with an overlay and no subtitles is refused, because the comparison cannot be made.
- `instagram_posts.write_all`, the delivery step, calls it just before the frame gates, through `frame_gates.refuse`. Only reels
  on their first delivery are read: a published reel is frozen and is never measured.

The reels that had the defect were fixed at the cause in each reel's own window: the overlay stops where the same words
start as speech, or is removed where the whole line is spoken at once.

## Alternatives rejected

- **Compare all text in the scene with the captions.** It refuses every phone message and sign that a character reads,
  which the ruling keeps.
- **Give `stick.card` and `key_line` a marker attribute and look for that.** It changes the drawing record of an approved
  part for the sake of a check, and the geometry already identifies them.
- **Fix the helpers so they cannot repeat a line.** Neither helper is given the captions, and each is called by the reel
  with a line of its own, so the comparison belongs at delivery, where both exist.
- **A frame check on rendered pixels.** It needs OCR and a render, while the scene states the same facts exactly.

## Consequences

- A new reel with a repeating overlay fails delivery with the reel, the overlay kind and the words.
- A new overlay helper is not covered until the gate learns its drawing. A change to `stick.CARD` or the key line's
  geometry is followed by the gate, which reads those constants.
- A project with no scene beside its master is skipped, not refused: there is nothing to read.
