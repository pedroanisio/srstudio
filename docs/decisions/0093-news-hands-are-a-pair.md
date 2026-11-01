---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0089: The News anchors' hands are a pair

- Status: accepted (2026-11-01), on arc4d3's order of that day
- Deciders: arc4d3; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0071](0071-news-anchor-head-rigs.md)
- Back to the [library README](../../README.md)

## Context

Through version 5 both arms drew the same hand. With Gus's palms to the camera the thumb on the frame's right pointed
inward, which is right, and the one on the frame's left pointed outward: a left hand on his right arm. The same drawing
also put the thumbs of the two fists holding his phone on opposite edges of it. arc4d3 reported it from `safe-from-you`
on 2026-11-01 (Slack 1793545038.063029), and asked that the structural fault become a rule that refuses at build time.

## Decision

Version 6 of `news-gus` and `news-vera` makes the hands typed pairs. `news_arms.DRAWN_FOR` says which arm each shape is
drawn for, and `news_arms.Hand` is a shape on an arm: on the other arm it is the same drawing mirrored, so a thumb
follows its side. `Hand.on` refuses a hand placed on the other arm. Faces, costumes, arms and head rigs are version 5's.

Versions before 6 keep drawing what went out, so rebuilding a published reel does not change it. Queued reels move to
version 6, `came-in-for` included, which leaves version 3.

## Alternatives rejected

- A second drawn hand per shape: two drawings to keep alike, the fault this fixes.
- Mirroring at the arm's group: it would flip the sleeve's shading and the cuff, which are not handed.
- Changing versions 2 to 5 in place: an approved version is immutable, and published reels pin them.
