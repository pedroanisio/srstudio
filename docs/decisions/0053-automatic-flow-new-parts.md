---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0053: A new reel's new parts are approved by the automatic flow

- Status: accepted (2026-10-30), from the operator's words: "eu nao vou revisar os videos, esse fluxo tem que ser
  automatico e passar pelos gates do processo."
- Deciders: the operator (pedroanisio), recorded by Claude Opus 5.5 in Claude Code
- Applies [ADR 0047](0047-character-versions.md) to the 24 reels of [the broad batch](../backlog/broad-24.md)
- Back to the [library README](../../README.md)

## Context

A release pins approved versions, and a delivery compares a build's record with those pins, so a reel that draws a
proposed part cannot be delivered. The broad batch drew 152 new version-1 parts, props and locations, and no character.
The operator does not review these videos: quality is held by the engine, the agents and the gates.

## Decision

1. Each of the 152 records is `approved` at version 1 and carries the operator's sentence as its `approval`.
2. Each reel pins what its build drew, read from the build's record, so a later version cannot change it.
3. This covers version 1 of props and locations in this batch. New character looks, approved hearings (`Line(heard=)`)
   and freezing a published reel stay the operator's decisions.

## Alternatives rejected

- **Shipping without pins.** The delivery gate refuses a record that does not match the release.
- **Leaving the parts proposed behind a bypass of the gate.** A gate with an exception proves nothing.
- **A review page for the 152.** The operator ruled it out.

## Consequences

- The digest test holds each approved drawing, so changing one of the 152 now means a new version.
- A catalog reader cannot tell these approvals from an approval given on a proof clip except by the words recorded.
