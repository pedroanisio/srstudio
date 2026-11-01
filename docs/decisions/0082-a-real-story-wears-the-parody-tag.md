---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0082: A real story wears the PARODY tag

## Context

ADR 0060 gave each kind of News Compiler reel its own code: a fictional reel the BREAKING banner and the PARODY tag, a
real one the source card and its corner credit. A real reel therefore had no tag. These reels quote real companies, real
executives and real papers, and arc4d3 ruled on 2026-11-01 (Slack 1793540353.039279) that the tag must be on screen from
the first frame to the last, with the source credit elsewhere.

## Decision

`Story(parody=True)` draws the PARODY tag from 0 to the end of the reel, in its usual corner, and moves the credit to the
top row just left of it. The banner stays on fictional reels only. `source_card` refuses a credit that would run into
the show's name.

## Consequences

The two codes no longer differ by the tag: a viewer tells the kinds apart by the source card, the credit and the banner.
Reels approved before the ruling keep the picture they were approved with, so `parody` defaults to off for them, and a
new real reel has to set it.

## Rejected

- **The credit under the show's name.** The caption band starts just below that row, so a chip there sits against it.
- **The credit on the lower-third.** The lower-third stops while a phone is up, and the source must never leave the screen.
