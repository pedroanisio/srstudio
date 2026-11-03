---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0225: Static checks stay in the gate

- Status: accepted (2026-11-03, the orchestrator's refactor item after a defect reached develop past the gate)
- Back to the [library README](../../README.md)
- Builds on [ADR 0221](0221-a-five-minute-gate.md)

## Context

The five-minute gate runs every test not marked `slow`, and a full-tier run decides what is slow by measuring it:
over two seconds, or seen taking the GPU, or in a file whose slow tests add up past 10 s (ADR 0221). A measurement
is the processor's time on a loaded machine, so it moves with whatever else the machine runs.

`tests/test_gpu.py::test_every_engine_call_that_uses_the_gpu_takes_the_lock` is an AST scan of the library and the
tools: it reads source and runs nothing. It takes about 1.9 s alone; one loaded full-tier run measured it at 10.08 s,
the table listed it, its 10.08 s pushed `tests/test_gpu.py` past the file bound, and the gate stopped running it. A
smoke render in `tools/engine_install.py` outside `gpu.held()` then reached develop: the one check written to catch
it had been moved out of the gate by one noisy number.

## Decision

- **`@pytest.mark.static` pins a test to the gate.** It says the test reads source or data and runs no engine, takes
  no GPU and starts no render, so its time is the processor's alone. `tests/conftest.py` never marks a static test
  `slow`: not when the table lists it, and not when its file leaves the gate whole.
- **The tier writer never lists a static test**, so no measurement of one can reach the table, and the file bound
  adds up only the tests that are not pinned.
- **A pin that is provably wrong is refused, not obeyed.** A static test that asks for the engine fails collection;
  a `--write-tiers` run that saw a static test take the GPU lock, or measured it past `STATIC_CEILING` (30 s, fifteen
  times the bound), writes no table and names the test (`tiers.StaticPinError`, raised as a usage error). Load
  inflates a static check a few times over; past the ceiling, the test is no static check.
- **Pinned now**: the source scans whose purpose is to fail a change in another file: the GPU-lock scan, the scan
  for test-module imports, the decision-record citation scan, the rclone road scan and the skeleton's import
  boundary. `tests/test_tiers.py` reads each pin from the source, so removing one fails a test.
- A pinned test still counts against the gate's budget, and a gate over budget still names its slowest tests.

## Rejected

- **A higher bound, or the median of several runs.** Every bound is crossed by enough load, and the table is written
  by one run; a test whose job is to guard the gate should not depend on the next run's load at all.
- **Exempt every test that asks for no engine.** Most of the measured slow tests run no engine and are slow for real
  (geometry solves, document builds); they belong in the full tier.
- **Edit the table by hand to drop the scan.** The next full run writes it back (ADR 0221: the table is never written
  by hand).
