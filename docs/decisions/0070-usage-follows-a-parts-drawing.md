---
generated-by: Claude Sonnet 5.5 (claude-sonnet-5-5) in Claude Code
---

# ADR 0070: The usage measure follows the drawing a part only calls

- Status: proposed; implemented 2026-10-31 on `fix/usage-performers` (`srstudio.usage`; tests in `tests/test_usage.py`).
  It extends [ADR 0017](0017-measured-part-usage.md) and [ADR 0032](0032-releases-recorders-and-discovery.md).
- Deciders: worskpace-e5 (orchestrator), pending review; implementation drafted by Claude Sonnet 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

`srstudio usage` records a part as used when the code object of its registered builder runs. The News and Host kits
register one-pose conveniences (`news_kit.vera`, `news_kit.gus`, `host_kit.lint`) whose whole body is
`return perform(...)`, and every shot draws the anchors and the host by calling `perform` itself. The registered
function never runs in a reel, so the measure reported `news-vera`, `news-gus` and `host-lint` unused although they are
on screen in every shot (2026-10-31, 145 episodes). The unused list is what the catalog, the gallery coverage check and
the pin check read, so a part drawn only through its performer could never be pinned by a release.

## Decision

1. A function builder that ends by returning a call, by name, to a function of its own module that is not itself a
   registered part is a **delegate** of that function. `usage._delegates` finds these from the builders' source.
2. When the delegated function runs, the call counts for the part whose constants it matches: each delegate records the
   constant arguments of its call by parameter name (`who="vera"`), and a frame matches when its arguments equal them.
   A call that matches exactly one part credits it; one that matches several (parts that pass nothing to tell them
   apart) credits none.
3. Nothing is named in the measure and no kit changes: the registrations stay as they are, so a kit that is being
   redrawn is not touched by it.

## Consequences

- A real measure of 145 episodes differs from the one before only by `news-gus` and `news-vera` in `everyday-breaking`
  and `real-roast` and `host-lint` in `unwritten-rules-group-chat`; nothing else is added or removed.
- The same shape exists elsewhere, in drawings that two or more parts call with nothing to tell them apart (`blob.blob`
  for pip, bo, juno and remy, `toon_cast.figure`, `collage.figure`, `saga._person`), and in `gloss._person`, told apart
  by its `colour`. Every part of them was already measured used, and the ambiguous ones stay credited only by their own
  builders, as before.
- A build records what it draws (`parts.json`), so a release for a News or Host reel must now pin `news-vera`,
  `news-gus` or `host-lint` at the version drawn. That is the gate working as it was meant to.

## Rejected alternatives

- **Declare the performer on each registration** (`register(..., draws=perform)`). A hand-written declaration drifts, the
  reason ADR 0017 measures instead of declaring, and it edits `news_kit.py`, which another branch is redrawing.
- **List `news-vera`, `news-gus` and `host-lint` as untraced in the coverage test.** It hides the defect and keeps them
  out of every pin.
- **Credit any part whose builder calls a helper that runs.** A helper shared by many parts would credit them all.
