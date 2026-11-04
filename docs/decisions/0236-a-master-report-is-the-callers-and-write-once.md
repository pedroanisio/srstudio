---
generated-by: Claude Opus 5.5 (claude-opus-5-5) in Claude Code
---

# ADR 0236: A master's --report is the caller's path, and write-once

- Status: proposed (2026-11-04)
- Deciders: the operator; written by Claude Opus 5.5 in Claude Code
- Follows [ADR 0078](0078-strict-findings-at-first-delivery.md) and
  [ADR 0170](0170-approved-files-are-write-once.md)
- Back to the [library README](../../README.md)

## Context

`srstudio master <scene> -- --report <path>` passed the path to the engine untouched, and the engine runs in the
document's folder. A relative path given from the workspace, as the reel skill writes it
(`generated/episodes/<slug>/qa/render-report.json`), landed at
`generated/episodes/<slug>/generated/episodes/<slug>/qa/render-report.json`, and a later encode overwrote the report
of an earlier one there. The render report is the evidence the first-delivery gate reads for `--strict` findings
(ADR 0078); ADR 0170 made the master write-once, but left the report a "measurement of the last encode, re-run each
time".

## Decision

`srstudio.master.encode` reads a `--report PATH` (or `--report=PATH`) among the engine arguments as the caller's:

- a relative path is resolved against the caller's working folder;
- the report is write-once, like the master: a report already at its place (each output's place when the name holds
  `{id}`) is refused with `files.WriteOnceError` before the engine starts; with `--next` the new report goes to the
  next free name, `render-report-v2.json`;
- the engine writes the report into a private stage beside its place, and it is installed from there with
  `files.install_once`, so a report that appears during the encode is kept and the new one goes beside it;
- `{id}` may stand only in the file name, a missing path or a second `--report` is a `MasterError`;
- `Encoded.report` lists where the reports went, and `srstudio master` prints `report: <path>` for each.

A `report=` on the document's output is the document's own and is unchanged: the engine writes it beside the
document.

## Consequences

- A re-encode with `--report` over a report already there stops with exit 2 before any render, as one over a master
  does. Move the old report away by hand, or encode with `--next`.
- After `--next`, the first-delivery gate still reads `qa/render-report.json`, the first encode's report. Promoting a
  `-v2` master and its report is an act of its own, as ADR 0170 says of masters.
- No master's drawing or encode changes: only where the report is written, and that it is never replaced.

## Rejected alternatives

- **Write `report-N` silently on every re-run.** A gate that reads the fixed name would read a stale report while the
  caller believed the new one was in place; a refusal names the conflict before the encode is spent.
- **Resolve against the document's folder and document it.** Every other path the caller gives `srstudio` is read
  from the working folder, and the reel skill already writes the path that way.
