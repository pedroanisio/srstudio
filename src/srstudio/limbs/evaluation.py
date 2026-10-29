"""Observed scene cost and blinded review records; absent ratings never become preference evidence."""

from __future__ import annotations

import ast
import hashlib
import inspect
import statistics
import textwrap
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from sr_core.scene import Scene

from .errors import LimbError
from .math3d import number
from .model import label
from .serialization import MAX_ITEMS, _decode

_CLOCK = time.perf_counter


@dataclass(frozen=True)
class Measurement:
    name: str
    repeats: int
    median_build_seconds: float
    min_build_seconds: float
    max_build_seconds: float
    xml_bytes: int
    nodes: int
    shapes: int
    source_lines: int
    scene_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


def measure(
    name: str, builder: Callable[[], Scene], *, repeats: int = 3, clock: Callable[[], float] = _CLOCK
) -> Measurement:
    """Measure building separately from schema validation; require byte-identical output across repetitions.

    Source lines describe only the supplied entry function, excluding blanks, comments and docstrings.
    They exclude library dependencies and human authoring time and must not be presented as either.
    """
    label(name, "measurement name")
    if type(repeats) is not int or not 1 <= repeats <= 10:
        raise LimbError("measurement repetitions must be an integer in 1..10")
    try:
        source = textwrap.dedent(inspect.getsource(builder))
    except (OSError, TypeError) as error:
        raise LimbError("measurement builder needs inspectable Python source") from error
    if len(source) > 100000:
        raise LimbError("measurement source exceeds its bound", code="budget")
    tree = ast.parse(source)
    doc_lines = {
        i
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        for i in range(node.lineno, (node.end_lineno or node.lineno) + 1)
    }
    source_lines = sum(
        bool(line.strip()) and not line.lstrip().startswith("#") and i not in doc_lines
        for i, line in enumerate(source.splitlines(), 1)
    )
    durations, hashes = [], []
    raw = b""
    scene = None
    for _ in range(repeats):
        start = number(clock(), "measurement start")
        scene = builder()
        elapsed = number(number(clock(), "measurement end") - start, "measurement duration")
        if elapsed < 0:
            raise LimbError("measurement clock moved backwards")
        durations.append(elapsed)
        if not isinstance(scene, Scene):
            raise LimbError("measurement builder must return a Scene")
        findings = scene.check(schema=True)
        if findings:
            raise LimbError("measured scene failed schema validation: " + str(findings[0]), code="quality")
        raw = scene.to_bytes()
        if len(raw) > 50 * 1024 * 1024:
            raise LimbError("measured scene exceeds the 50 MiB bound", code="budget")
        hashes.append(hashlib.sha256(raw).hexdigest())
    if len(set(hashes)) != 1:
        raise LimbError("measurement builder is not deterministic across repetitions", code="quality")
    assert scene is not None
    return Measurement(
        name,
        repeats,
        statistics.median(durations),
        min(durations),
        max(durations),
        len(raw),
        len(list(scene.iter())),
        len(list(scene.iter("shape"))),
        source_lines,
        hashes[0],
    )


@dataclass(frozen=True)
class Pair:
    id: str
    task: str
    baseline: str
    candidate: str

    def __post_init__(self) -> None:
        for field in ("id", "baseline", "candidate"):
            label(getattr(self, field), "review pair " + field)
        if not isinstance(self.task, str) or not 1 <= len(self.task) <= 512 or self.baseline == self.candidate:
            raise LimbError("review pair needs a task and distinct implementations")


@dataclass(frozen=True)
class Trial:
    id: str
    case: str
    task: str
    a: str
    b: str

    def public_dict(self) -> dict:
        return {"id": self.id, "task": self.task, "a": f"{self.id}-A.mp4", "b": f"{self.id}-B.mp4"}


def plan_trials(pairs: tuple[Pair, ...], *, seed: str) -> tuple[Trial, ...]:
    """Counterbalance A/B across tasks, with deterministic shuffled task order and an external private key."""
    label(seed, "review seed")
    if not 1 <= len(pairs) <= 100 or len({p.id for p in pairs}) != len(pairs):
        raise LimbError("review needs 1..100 uniquely named task pairs")

    def digest(value: str) -> bytes:
        return hashlib.sha256((seed + "\0" + value).encode()).digest()

    ordered = sorted(pairs, key=lambda p: digest(p.id))
    parity = digest("order")[0] % 2
    return tuple(
        Trial(
            f"trial-{i + 1:03d}",
            p.id,
            p.task,
            p.candidate if (i + parity) % 2 else p.baseline,
            p.baseline if (i + parity) % 2 else p.candidate,
        )
        for i, p in enumerate(ordered)
    )


@dataclass(frozen=True)
class Scores:
    clarity: int
    naturalness: int
    style_fit: int

    def __post_init__(self) -> None:
        if any(type(value) is not int or not 1 <= value <= 5 for value in asdict(self).values()):
            raise LimbError("review scores must be integers in 1..5")


@dataclass(frozen=True)
class Rating:
    trial: str
    reviewer: str
    preference: str
    a: Scores
    b: Scores
    notes: str = ""

    def __post_init__(self) -> None:
        label(self.trial, "rating trial")
        label(self.reviewer, "reviewer ID")
        if self.preference not in ("a", "b", "tie"):
            raise LimbError("review preference must be a, b or tie")
        if not isinstance(self.notes, str) or len(self.notes) > 2000:
            raise LimbError("review notes exceed the 2000 character bound")


def parse_ratings(data: object) -> tuple[Rating, ...]:
    if not isinstance(data, dict) or set(data) != {"schema", "ratings"}:
        raise LimbError("rating document needs only schema and ratings fields")
    if data["schema"] != "srstudio.limbs.ratings/1.0.0":
        raise LimbError("unsupported rating schema")
    result: tuple[Rating, ...] = _decode(tuple[Rating, ...], data["ratings"], "ratings", [MAX_ITEMS])
    return result


def summarize(trials: tuple[Trial, ...], ratings: tuple[Rating, ...], *, minimum_reviewers: int = 5) -> dict[str, Any]:
    """Descriptive counts and means only. The caller supplies reviews; this does not verify reviewer identity."""
    if type(minimum_reviewers) is not int or not 1 <= minimum_reviewers <= 1000:
        raise LimbError("minimum reviewers must be an integer in 1..1000")
    if not 1 <= len(trials) <= 100 or len(ratings) > 10000:
        raise LimbError("review summary exceeds its bounds", code="budget")
    lookup = {trial.id: trial for trial in trials}
    if len(lookup) != len(trials):
        raise LimbError("duplicate review trial")
    seen = set()
    counts: dict[str, set[str]] = {trial.id: set() for trial in trials}
    accumulators: dict[str, dict[str, Any]] = {}
    for trial in trials:
        for implementation in (trial.a, trial.b):
            accumulators.setdefault(
                implementation, {"ratings": 0, "wins": 0, "ties": 0, "clarity": [], "naturalness": [], "style_fit": []}
            )
    for rating in ratings:
        if rating.trial not in lookup:
            raise LimbError(f"unknown review trial {rating.trial}")
        key = (rating.trial, rating.reviewer)
        if key in seen:
            raise LimbError("duplicate rating by the same reviewer for one trial")
        seen.add(key)
        counts[rating.trial].add(rating.reviewer)
        trial = lookup[rating.trial]
        for side in ("a", "b"):
            row = accumulators[getattr(trial, side)]
            row["ratings"] += 1
            row["wins"] += rating.preference == side
            row["ties"] += rating.preference == "tie"
            for field, value in asdict(getattr(rating, side)).items():
                row[field].append(value)
    results = {
        name: {
            "ratings": row["ratings"],
            "wins": row["wins"],
            "ties": row["ties"],
            **{
                field + "_mean": statistics.mean(row[field]) if row[field] else None
                for field in ("clarity", "naturalness", "style_fit")
            },
        }
        for name, row in accumulators.items()
    }
    return {
        "status": "awaiting_ratings"
        if not ratings
        else "complete"
        if all(len(group) >= minimum_reviewers for group in counts.values())
        else "partial",
        "reviewers": len({rating.reviewer for rating in ratings}),
        "ratings": len(ratings),
        "minimum_reviewers_per_trial": minimum_reviewers,
        "trial_reviewers": {name: len(group) for name, group in counts.items()},
        "results": results if ratings else None,
        "provenance": "caller-supplied ratings; identities not verified",
    }
