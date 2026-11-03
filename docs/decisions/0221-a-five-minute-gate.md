---
generated-by: Claude Code (Claude Opus 5.5)
---

# ADR 0221: The gate takes five minutes, and the full suite is its own tier

- Status: accepted (2026-11-03, the operator: "o budget do gate eh 5 minutos")
- Back to the [library README](../../README.md)
- Builds on [ADR 0141](0141-gates-live-in-the-repository.md)

## Context

`tools/gate.sh` ran the whole suite in one process: about two hours on 2026-11-03, for 23,805 tests. A twelve-worker
run (`pytest-xdist`) of the same suite still took 1,446 s, and 8,105 s of processor time cannot fit five minutes on
twelve cores. The cost is concentrated: the 120 slowest tests took 5,649 s of it, the slowest alone 1,242 s, and most
of them render with the engine, whose calls take the one GPU in turn (ADR 0171), so they wait on each other however
many workers there are.

## Decision

- **Two tiers.** A test marked `slow` runs only in the full tier; the gate runs every other test.
- **What is slow is decided by code, not by hand.** `tests/conftest.py` marks a test `slow` when it asks for the
  engine (the `scene_render` fixture), or when `tests/tiers.json` lists it. A full-tier run writes that table
  (`pytest --write-tiers PATH`, which `tools/gate.sh --full` passes): every test it measured over two seconds, setup
  and teardown included, or saw take the GPU lock. The writer refuses a failing run or one that deselected tests, and
  `tests/tiers.py` parses the table into a typed form that refuses unknown fields, bad numbers and entries that do not
  belong in it.
- **The gate:** `tools/gate.sh SHA` runs format and lint, types beside the tests, and `pytest -n auto --dist worksteal
  -m "not slow" --cov` with the 80 % branch-coverage floor. It is stopped at `GATE_BUDGET` (300 s) from the moment it
  holds the machine's gate lock, and a run over budget fails, naming its slowest tests. One gate runs at a time.
- **The full tier:** `tools/gate.sh --full SHA` runs every test in parallel, with coverage, and writes a fresh table.
  It passes before develop moves to main, and its table is committed when the split between tiers has drifted.
- **A new test** with no measurement runs in the gate unless it asks for the engine. If it is slow, the gate goes over
  budget and says which test; the full tier's table then moves it.
- The first table came from a passing full run on 2026-11-03 (23,822 tests, 95.11 % branch coverage, 2,615 s on
  twelve workers): 1,011 tests measured slow, 163 of them for the GPU. With the tests that ask for the engine, the
  gate leaves out 1,176 tests and runs 22,646.
- `pytest-xdist` joins the `test` extra. It replaces a parallel runner the project would otherwise write: process
  workers, load balancing and the merging of results and coverage.

## Rejected

- **Raise the budget, or run the full suite in parallel as the gate.** Measured at 1,446 s on twelve workers.
- **A hand-kept list of slow tests.** It goes stale silently; a measured table is rewritten by the run that proves it.
- **Mark only the tests that ask for `scene_render`.** Twenty test files find the engine on their own, and many slow
  tests run no engine at all.
- **Skip the slow tests.** They still run, in the full tier, and nothing lands on main without it.
- **Choose the gate's tests from coverage data** (rejected in ADR 0141 as well): finer, and it needs a full run to
  refresh, as the table does, while also needing a coverage map per test.
