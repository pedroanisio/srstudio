"""The gate's two tiers (ADR 0221).

The five-minute gate runs every test except those marked ``slow``; the full tier runs them all. A test is ``slow``
when it asks for the engine (the ``scene_render`` fixture), or when :data:`TABLE` lists it: a full-tier run measured it
over :data:`BOUND` seconds, or saw it take the GPU lock, which serialises every worker that wants it. A file whose
listed tests add up past :data:`FILE_BOUND` leaves whole: a cache its tests share charges its cost to whichever test
runs first in a worker, a different one each run, so the cost belongs to the file. The table is
written by ``pytest --write-tiers tests/tiers.json`` on a full run, never by hand.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "1.0.0"
BOUND = 2.0  # seconds: a gate test above it, on a loaded twelve-worker run, leaves the gate
FILE_BOUND = 30.0  # seconds: a file whose measured slow tests add up past it leaves the gate whole
TABLE = Path(__file__).with_name("tiers.json")
ENGINE_FIXTURES = frozenset({"scene_render"})


class TierTableError(ValueError):
    """The tier table is not what :func:`render` writes."""


@dataclass(frozen=True)
class Run:
    """One test as a full-tier run measured it: setup, call and teardown seconds, and whether it took the GPU."""

    seconds: float
    gpu: bool

    @property
    def slow(self) -> bool:
        return self.gpu or self.seconds > BOUND


def _run(node: str, entry: object) -> Run:
    if not isinstance(entry, dict) or set(entry) != {"seconds", "gpu"}:
        raise TierTableError(f"{node}: fields must be seconds and gpu, got {entry!r}")
    seconds, gpu = entry["seconds"], entry["gpu"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
        raise TierTableError(f"{node}: seconds must be a finite number, at least 0, got {seconds!r}")
    if not isinstance(gpu, bool):
        raise TierTableError(f"{node}: gpu must be true or false, got {gpu!r}")
    run = Run(float(seconds), gpu)
    if not run.slow:
        raise TierTableError(f"{node}: neither over {BOUND} s nor on the GPU, so it belongs in the gate")
    return run


def parse(data: object) -> dict[str, Run]:
    """The table's tests, each checked; :class:`TierTableError` on anything :func:`render` would not write."""
    if not isinstance(data, dict):
        raise TierTableError(f"the tier table must be an object, got {type(data).__name__}")
    if set(data) != {"schema_version", "bound_seconds", "tests"}:
        raise TierTableError(f"the tier table's fields must be schema_version, bound_seconds, tests: {sorted(data)}")
    if data["schema_version"] != SCHEMA:
        raise TierTableError(f"tier table schema {data['schema_version']!r}, this code reads {SCHEMA}")
    if data["bound_seconds"] != BOUND:
        raise TierTableError(
            f"the table was measured against a {data['bound_seconds']} s bound, not {BOUND}: rewrite it"
        )
    tests = data["tests"]
    if not isinstance(tests, dict):
        raise TierTableError("tests must be an object of node id to measurement")
    for node in tests:
        if not isinstance(node, str) or not node.startswith("tests/") or "::" not in node:
            raise TierTableError(f"not a node id under tests/: {node!r}")
    return {node: _run(node, entry) for node, entry in tests.items()}


def load(path: Path = TABLE) -> dict[str, Run]:
    return parse(json.loads(path.read_text()))


def _up(seconds: float) -> float:
    """Hundredths, rounded up, so a test just over the bound still reads over it."""
    return math.ceil(round(seconds * 100, 6)) / 100


def render(runs: dict[str, Run]) -> str:
    """The table for ``runs``: only the tests that leave the gate, sorted, one per line."""
    kept = {node: run for node, run in sorted(runs.items()) if run.slow}
    lines = [
        f"    {json.dumps(node)}: {json.dumps({'seconds': _up(run.seconds), 'gpu': run.gpu})}"
        for node, run in kept.items()
    ]
    body = ",\n".join(lines)
    return (
        f'{{\n  "schema_version": "{SCHEMA}",\n  "bound_seconds": {BOUND},\n  "tests": {{\n{body}\n  }}\n}}\n'
        if lines
        else f'{{"schema_version": "{SCHEMA}", "bound_seconds": {BOUND}, "tests": {{}}}}\n'
    )


def heavy_files(measured: dict[str, Run]) -> frozenset[str]:
    """The files whose measured tests add up past :data:`FILE_BOUND` seconds."""
    totals: dict[str, float] = {}
    for node, run in measured.items():
        path = node.split("::", 1)[0]
        totals[path] = totals.get(path, 0.0) + run.seconds
    return frozenset(path for path, seconds in totals.items() if seconds > FILE_BOUND)


def full(
    node: str, fixtures: set[str] | frozenset[str], measured: dict[str, Run], heavy: frozenset[str] | None = None
) -> bool:
    """Whether the test at ``node``, asking for ``fixtures``, runs in the full tier only."""
    files = heavy_files(measured) if heavy is None else heavy
    return bool(ENGINE_FIXTURES & fixtures) or node in measured or node.split("::", 1)[0] in files
