---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0229: A build reports checks actually executed and preserves repair diagnostics

- Status: accepted (2026-11-04)
- Back to the [library README](../../README.md)
- Builds on [ADR 0141](0141-gates-live-in-the-repository.md) and [ADR 0221](0221-a-five-minute-gate.md)

## Context

`74b15444` introduced `build --json` and `--require-check`; `f7fd8ef3` limited frame checks to published
outputs and handled successful script exits and plugin logs. Those changes lacked a decision record.
An exit code alone cannot tell an agent whether a build measured anatomy, validated a scene or merely wrote
a file. A previous scene in the same directory is not evidence from the current invocation. Plugin chatter
must not corrupt machine-readable output or change a quiet SDK error's established diagnostic shape.

## Decision

- Scope evidence to a build with a context-local report. Instrumented SDK operations register artifacts and
  check executions; the CLI never discovers success by scanning old files. `srstudio.build/1.1.0` includes
  absolute artifact paths and per-check `passed`, `failed` or `skipped` statuses with execution details.
- The checks are `sdk`, `schema`, `usage`, `anatomy`, `text` and opt-in `motion-quality`. Missing dependencies,
  absent executions and unavailable measurements are skipped. Failures dominate skips, which dominate passes.
  Repeating `--require-check NAME` requires every execution of each selected check to pass, in text and JSON
  mode, including when a builder finishes with `sys.exit(0)` or `sys.exit()`.
- `ROOT` explicitly enables usage recording and post-build frame checks. The CLI measures each scene published
  in this invocation, including custom file names and multiple outputs, excluding audio-only scenes. Direct
  scene writers can register an artifact explicitly; registration alone does not imply SDK/schema validation.
- Motion quality records the selected profile, policy, sampling provenance, metrics and structured findings.
  No selected profile or no limits is skipped. Insufficient derivative samples and breached limits fail evidence.
  Warn policy permits emission unless the check is required; error policy preserves evidence before refusal.
  Validated preparation reused with identical inputs is identified as cached evidence. Numeric limb limits are
  distinct from whole-body dynamics, rendered visual checks and human temporal approval.
- JSON success is stdout; diagnostics are stderr. Builder/plugin stdout and stderr, including native writes and
  child-process output, are captured with bounded retained logs. Build results retain their existing log fields.
  Failed plugin imports add only nonempty log fields to `context`; quiet failures retain their previous shape.
  SDK errors retain their repair fields; foreign plugin exceptions and exits become `plugin.import` failures.
- All library exception classes, including internal lookup wrappers, inherit `SrstudioError`. A lookup wrapper
  carries the original diagnostic so JSON mode can retain both its repair fields and the input-error exit status.
  Failure responses retain available build evidence at `context.build`; published artifacts may survive a later
  verification failure, so a retry must inspect them rather than assuming the build was transactional.

## Alternatives and limits

A boolean verified flag conflates missing checks with success. Measuring every XML file in a directory can pass
stale outputs or judge an unrelated build. Ignoring successful SystemExit bypasses requested verification.
Changing existing tests to accept empty plugin log fields would broaden a diagnostic contract unnecessarily.
The report measures instrumented operations; it cannot infer checks performed privately by arbitrary scripts.

## Verification and history

Tests exercise artifact provenance, required failed/skipped checks, successful and unsuccessful script exits,
quiet/noisy plugin failures, original SDK repair fields, and the common exception hierarchy. Motion tests cover
warn/error policies, cached preparation, scope refusals, insufficient samples and compiler backends. Run the
repository gate in the shared environment, in addition to targeted tests and selected renderer checks.

This record documents the rationale missing from the already-published `74b15444` without replacing that commit
or requiring a force-push. Follow-up commits include the problem, final behavior and actual validation scope in
their bodies. A local commit is not publication; check the remote head after a successful push.
