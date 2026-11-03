# Agent instructions

Before choosing an ADR number, read `docs/decisions/reserved.json` and inspect
the records already present in `docs/decisions/`. Choose a number absent from
both, or use your existing reservation under its exact reserved name. Never
reuse another contributor's reservation, including when committing directly
to `develop`.

For work that spans sessions or branches, record the reservation in the
repository so other agents can see it. Recheck reservations before committing
an ADR, and run `python -m pytest -q tests/test_decisions.py`. Remove only the
matching reservation when its ADR lands on `develop`.
