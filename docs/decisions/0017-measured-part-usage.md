---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0017: Which parts the episodes use is measured, not declared

- Status: accepted and implemented, 2026-10-28 (`srstudio.usage`, `srstudio usage`, `srstudio page --usage`,
  `tests/test_usage.py`, `tests/test_catalog_page.py`)
- Deciders: the operator (pedroanisio), implementation drafted by Claude Opus 5.5 in Claude Code
- Back to the [library README](../../README.md)

## Context

The catalog lists every registered part with the episodes that use it. Those episodes came from the `episodes=`
argument of `register`, which is written by hand. Episodes 09 and 10 added new rooms, props and characters, and the
declarations had drifted: 19 parts that episodes draw, among them `juno`, `remy`, `reception` and
`conference-room`, declared no episode at all. A question as simple as "which characters, locations and props are unused?" had no reliable answer.

## Decision

1. **`usage.trace()`** records every registered part called inside a block. It matches the code objects of each
   builder under a profiler hook: a function part, or the methods a class part defines itself. A call counts however
   it is reached: through a module attribute, an imported name, the registry, or another part that draws it (a
   location drawing its props). Looking up a class part does not count; running its drawing does.
2. **`usage.measure()`** rebuilds each episode project on a copy, in a fresh interpreter, with the episode's own
   script. An episode whose build fails stops the run with its name. A project with no script is reported as not
   measured.
3. **`srstudio usage`** writes the report as JSON (schema `1.0.0`): the parts each episode used, the unmeasured
   projects, and every registered part with its kind, style and measured episodes. `Report.read` refuses an unknown
   schema, unknown fields and wrong types.
4. **`srstudio page --usage`** uses the report for the registry table, the gallery chips and the gallery coverage
   check. It also adds the lists of used and unused characters, locations and props. Without `--usage`, the page
   keeps the declared episodes.

## Rejected alternatives

- **Correcting the `episodes=` declarations by hand.** That would fix today's drift and drift again with the next
  episode. Nothing would check the declarations.
- **Searching the episode scripts for part names.** A location draws its props without the script naming them, and
  parts are reached through the registry and through imported names. A text search misses both.
- **Reading the rendered scene XML.** Parts leave no stable marker in the scene, and a part can draw shapes that
  another part also draws.

## Consequences

- Measuring rebuilds every episode, so it is a separate command and not part of every page build.
- The catalog's coverage check now follows real usage, so a part that a new episode draws must get a gallery item.
- The `episodes=` declarations remain as documentation for library users who do not run `srstudio usage`.
