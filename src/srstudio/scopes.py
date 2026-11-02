"""The master's levels (ADR 0172): broadcast-illegal codes, out-of-gamut and oversaturated samples, read with
``scene-render scopes <master> --step 5 --format json``.

A sample outside the legal range of its source (Y below 16 or above 235 in 8-bit limited range), a colour no RGB
display can show, or a chroma past the engine's limit is a defect of the master, and each one fails at the default
limit of 0: the fraction of samples must be exactly 0. Clipping (samples at the code values' ends) is measured and
reported but never gated: a white wall or a black frame is clipped by design.

The engine's answer is parsed into :class:`Levels`, and any answer that is not the envelope and schema this module
knows (another format, a failed run, a missing measure, a number out of ``[0, 1]``) is a :class:`ScopesError`, never a
pass. The idea is pnkit's ``tools/scopes_check.py``.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import SrstudioError
from .social import Drift

__all__ = [
    "FORMAT",
    "LIMITS",
    "MEASURES",
    "SCHEMA",
    "STEP",
    "Finding",
    "Levels",
    "Limits",
    "ScopesError",
    "judge",
    "lines",
    "measure",
    "parse",
    "scope_defects",
    "summary",
]

FORMAT = "scene-render-cli/1"
SCHEMA = "scene-render-scopes/1"
STEP = 5  # every fifth frame: 128 frames of a 26 s reel at 24 fps
MEASURES = ("illegal", "out_of_gamut", "oversaturated")
_CHANNELS = ("r", "g", "b", "y")
_TAIL = 400

Run = Callable[..., "subprocess.CompletedProcess[str]"]


class ScopesError(SrstudioError, ValueError):
    """The engine's levels could not be read: it did not run, failed, or answered in a shape this module refuses."""


def _fail(message: str, code: str = "scopes.answer") -> ScopesError:
    return ScopesError(message, code=code)


def _fraction(value: object, said: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise _fail(f"{said} must be a finite number, got {value!r}")
    if not 0.0 <= value <= 1.0:
        raise _fail(f"{said} must be a fraction of the samples, between 0 and 1, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class Limits:
    """The largest fraction of samples each measure may reach. 0 by default: one sample fails."""

    illegal: float = 0.0
    out_of_gamut: float = 0.0
    oversaturated: float = 0.0

    def __post_init__(self) -> None:
        for name in MEASURES:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int | float) or not 0.0 <= value <= 1.0:
                raise _fail(f"the {name} limit must be a fraction between 0 and 1, got {value!r}", "scopes.limit")


LIMITS = Limits()


@dataclass(frozen=True)
class Levels:
    """What a check reads from one master: the fraction of samples that are illegal (``None`` when the source has no
    legal range, as a full-range or float source has none), out of gamut, oversaturated, and the largest clipped
    fraction of any channel at either end."""

    file: str
    frames: int
    step: int
    illegal: float | None
    out_of_gamut: float
    oversaturated: float
    clipped: float


@dataclass(frozen=True)
class Finding:
    """One measure past its limit."""

    measure: str
    value: float
    limit: float

    def __str__(self) -> str:
        return f"{self.measure} {_percent(self.value)} > {_percent(self.limit)}"


def _percent(value: float) -> str:
    return f"{value * 100:.4g}%"


def _object(value: object, said: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise _fail(f"{said} is not an object")
    return value


def _key(data: Mapping[str, Any], name: str, said: str) -> Any:
    if name not in data:
        raise _fail(f"{said} has no {name}")
    return data[name]


def parse(raw: str | bytes) -> Levels:
    """The :class:`Levels` in the engine's ``--format json`` answer ``raw``, or a :class:`ScopesError`."""
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise _fail(f"the engine's answer is not JSON: {str(raw)[:_TAIL]!r}") from None
    envelope = _object(data, "the engine's answer")
    if _key(envelope, "format", "the answer") != FORMAT:
        raise _fail(f"the answer's format is {envelope['format']!r}, not {FORMAT!r}")
    if _key(envelope, "command", "the answer") != "scopes":
        raise _fail(f"the answer's command is {envelope['command']!r}, not 'scopes'")
    if _key(envelope, "ok", "the answer") is not True or _key(envelope, "exit_code", "the answer") != 0:
        raise _fail(f"the engine failed (exit {envelope.get('exit_code')!r}): {envelope.get('error')!r}")
    result = _object(_key(envelope, "result", "the answer"), "the answer's result")
    if _key(result, "schema", "the result") != SCHEMA:
        raise _fail(f"the result's schema is {result['schema']!r}, not {SCHEMA!r}")
    file = _key(result, "file", "the result")
    if not isinstance(file, str):
        raise _fail(f"the result's file must be a path, got {file!r}")
    frames = _object(_key(result, "frames", "the result"), "the result's frames")
    analysed, step = _key(frames, "analysed", "frames"), _key(frames, "step", "frames")
    for name, value in (("analysed", analysed), ("step", step)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise _fail(f"frames {name} must be a whole number, at least 1, got {value!r}")
    levels = _object(_key(result, "levels", "the result"), "levels")
    illegal = _key(levels, "illegal", "levels")
    saturation = _object(_key(levels, "saturation", "levels"), "levels saturation")
    clipping = _object(_key(levels, "clipping", "levels"), "levels clipping")
    clipped = [
        _fraction(_key(_object(_key(clipping, end, "clipping"), f"clipping {end}"), c, f"clipping {end}"),
                  f"clipping {end} {c}")
        for end in ("black", "white")
        for c in _CHANNELS
    ]  # fmt: skip
    return Levels(
        file=file,
        frames=analysed,
        step=step,
        illegal=None if illegal is None else _fraction(illegal, "illegal"),
        out_of_gamut=_fraction(_key(saturation, "out_of_gamut", "saturation"), "saturation out_of_gamut"),
        oversaturated=_fraction(_key(saturation, "above_limit", "saturation"), "saturation above_limit"),
        clipped=max(clipped),
    )


def judge(levels: Levels, limits: Limits = LIMITS) -> tuple[Finding, ...]:
    """Each measure of ``levels`` past its limit, in :data:`MEASURES` order. Clipping is never one."""
    found = []
    for name in MEASURES:
        value = getattr(levels, name)
        if value is not None and value > getattr(limits, name):
            found.append(Finding(name, value, getattr(limits, name)))
    return tuple(found)


def summary(levels: Levels) -> str:
    """The measures in one line, clipping marked as reported only."""
    illegal = "n/a" if levels.illegal is None else _percent(levels.illegal)
    return (
        f"illegal {illegal}, out_of_gamut {_percent(levels.out_of_gamut)}, oversaturated "
        f"{_percent(levels.oversaturated)}, clipped {_percent(levels.clipped)} (reported, not gated), "
        f"{levels.frames} frames at step {levels.step}"
    )


def measure(
    video: str | os.PathLike[str], *, engine: str | os.PathLike[str], step: int = STEP, run: Run = subprocess.run
) -> Levels:
    """Run ``engine scopes <video> --step <step> --format json`` and parse its answer. The engine only reads the
    video, and opens no GPU device for it (measured; ADR 0171)."""
    if isinstance(step, bool) or not isinstance(step, int) or step < 1:
        raise _fail(f"the step must be a whole number of frames, at least 1, got {step!r}", "scopes.step")
    command = [str(engine), "scopes", str(video), "--step", str(step), "--format", "json"]
    try:
        done = run(command, capture_output=True, text=True, check=False)
    except OSError as e:
        raise _fail(f"cannot run the engine {engine}: {e}", "scopes.engine") from None
    if done.returncode != 0:
        said = (done.stdout + done.stderr)[-_TAIL:]
        raise _fail(f"the engine failed on {video} (exit {done.returncode}): {said}", "scopes.engine")
    return parse(done.stdout)


def scope_defects(
    renders: str | os.PathLike[str],
    first: Mapping[str, str],
    engine: str | os.PathLike[str],
    *,
    limits: Limits = LIMITS,
    run: Run = subprocess.run,
) -> list[Drift]:
    """Each master on its ``first`` delivery (slug to video name) whose levels fail, or that cannot be measured: a
    reel the check cannot read is refused, not passed. Published reels are never in ``first``, so they stay frozen."""
    drift = []
    for video in first.values():
        path = Path(renders) / f"{video}.mp4"
        if not path.is_file():
            drift.append(Drift(video, f"no master at {path} to measure its levels"))
            continue
        try:
            found = judge(measure(path, engine=engine, run=run), limits)
        except ScopesError as e:
            drift.append(Drift(video, f"its levels cannot be read: {e}"))
            continue
        if found:
            drift.append(Drift(video, f"its levels fail: {', '.join(map(str, found))} (ADR 0172)"))
    return drift


def lines(videos: Sequence[str | os.PathLike[str]], engine: str | os.PathLike[str]) -> tuple[list[str], int]:
    """One line per video for ``srstudio scopes``, and its exit status: 0 clean, 1 a finding, 2 an error."""
    out, status = [], 0
    for video in videos:
        name = Path(video).name
        if not Path(video).is_file():
            out.append(f"{name}: no such file")
            status = 2
            continue
        try:
            levels = measure(video, engine=engine)
        except ScopesError as e:
            out.append(f"{name}: {e}")
            status = 2
            continue
        found = judge(levels)
        out.append(f"{name}: {summary(levels)}: " + (f"FAIL {', '.join(map(str, found))}" if found else "pass"))
        status = max(status, 1 if found else 0)
    return out, status
