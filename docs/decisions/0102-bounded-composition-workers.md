---
generated-by: OpenAI Codex (GPT-6)
---

# ADR 0102: Bounded composition workers

- Status: accepted (2026-11-01)
- Back to the [library README](../../README.md)

## Decision

Public vector preparation and scene compilation execute in a separate process.
A stdlib bootstrap installs a hard kernel address-space limit before the worker
imports the SDK. A parent-owned deadline and bounded nonblocking pipes control
startup, input transfer, execution and output. Process-group cleanup includes
descendants even after their leader exits. The host's limits and environment
remain unchanged; native math libraries use one thread in the worker.

The interface carries strict JSON records and base64 source bytes. Worker and
parent both validate their side of the protocol. The parent checks manifest and
content identities before publication, and typed diagnostics preserve repair
fields and known SDK cause types without importing classes named by a response.
No worker receives an output destination. The parent installs one complete
validated scene atomically, so resource failures cannot publish partial output.

`VectorSource` batches verification and compilation in one invocation.
`prepare_vector` remains an independently bounded geometry-inspection API, and
`PreparedVector` remains accepted with its evidence rechecked. Known manifest,
node and expansion failures are refused before launch. No automatic retry can
silently multiply the caller's work.

## Alternatives

- Cooperative elapsed-time checks cannot interrupt a stalled parser or native
  allocation. They remain useful inside compilation but do not own the deadline.
- Changing process limits in the host would constrain unrelated application work.
- A `preexec_fn` would run Python between fork and exec in a potentially threaded
  host. The standalone bootstrap avoids that dependency.
- `communicate()` with unconstrained capture would allow output to exhaust host
  memory. Bounded nonblocking pipes also handle workers that stop reading input.
- Pickling plans or callbacks would make executable objects part of the protocol.

## Scope

`RLIMIT_AS` limits each process's virtual address space, including mapped runtime
libraries. It does not measure RSS or cap aggregate/GPU memory. Host drawing
generation, bounded metadata intake and final publication remain host operations.
Installed SDK/approval records are reloaded in the worker; host-only runtime
patches do not cross the boundary. This is resource control for trusted workers,
not an isolation boundary for hostile programs that deliberately escape it.

Plate/print renderer sessions reuse the same process runner, with a private
working directory for relative scene assets, 64 KiB per diagnostic stream and
the smallest enclosing memory/deadline limits. Every enclosing invocation budget
counts failures and explicit retries. Atomic cache installation follows successful
rendering. Unscoped calls retain their existing behavior; host mesh preparation
and image decoding remain outside the session's process limits. Reusing the
runner keeps descendant cleanup and kernel-limit behavior shared with composition
workers instead of maintaining a second subprocess supervisor.

Plate/proxy source adapters and composition-budget integration remain open under SDK-P2-07.
The [composition guide](../composition-preflight.md) documents supported features;
the [runtime tests](../../tests/test_composition_runtime.py) and
[process tests](../../tests/test_bounded_process.py) exercise real kernel limits,
deadlines, descendant cleanup, malformed protocols and preserved outputs.
