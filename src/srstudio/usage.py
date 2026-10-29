"""Which registered parts each episode uses, measured from the calls its build makes.

A part's ``episodes=`` in :func:`~srstudio.registry.register` is written by hand and drifts as episodes are added.
:func:`trace` records instead every registered builder that runs: it matches the code objects of each builder (a
function, or the methods a class part defines itself) under a profiler hook, so a call counts however it is
reached (a module attribute, an imported name, the registry, or another part drawing it). :func:`measure` runs each
episode script on a copy of its project in a fresh interpreter (:func:`probe`) and gathers a :class:`Report`: the
parts each episode used, and with the registry, the parts no episode uses. ``srstudio usage`` writes it as JSON.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import CodeType

from . import registry

SCHEMA = "1.0.0"
_VERSION = re.compile(r"-\d+\.\d+\.\d+\Z")


class UsageError(RuntimeError):
    """An episode that failed to build, or a usage file that cannot be read."""


def _codes() -> dict[CodeType, str]:
    codes: dict[CodeType, str] = {}
    for entry in registry.entries():
        b = entry.builder
        if inspect.isclass(b):
            for value in vars(b).values():
                func = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
                if inspect.isfunction(func):
                    codes[func.__code__] = entry.name
        elif inspect.isfunction(b):
            codes[b.__code__] = entry.name
    return codes


@contextmanager
def trace() -> Iterator[set[str]]:
    """The names of the registered parts called inside the block (the set fills as they run)."""
    codes, used = _codes(), set()
    previous = sys.getprofile()

    def hook(frame, event, arg):
        if event == "call":
            name = codes.get(frame.f_code)
            if name is not None:
                used.add(name)

    sys.setprofile(hook)
    try:
        yield used
    finally:
        sys.setprofile(previous)


def _probe_here(script: Path, project: Path, args: Sequence[str], out: Path) -> None:
    """Run ``script PROJECT ARGS...`` in this interpreter, from the script's folder, and write the parts it used."""
    script = script.resolve()
    sys.argv = [str(script), str(project), *args]
    sys.path.insert(0, str(script.parent))
    os.chdir(script.parent)
    with trace() as used:
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise
    out.write_text(json.dumps(sorted(used)) + "\n")


def probe(script: Path, project: Path, args: Sequence[str], out: Path) -> None:
    """Build ``project`` with ``script`` in a fresh interpreter and write the parts it used to ``out`` (JSON list)."""
    command = [sys.executable, "-m", "srstudio.usage", str(Path(script).resolve()), str(Path(project).resolve())]
    command += [str(Path(out).resolve()), *args]
    run = subprocess.run(command, capture_output=True, text=True, check=False)
    if run.returncode != 0:
        raise UsageError(f"{Path(script).name} failed (exit {run.returncode}): {run.stderr.strip()[-600:]}")


@dataclass(frozen=True)
class Run:
    slug: str
    script: Path
    project: Path
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class Report:
    episodes: Mapping[str, tuple[str, ...]]  # slug -> the parts its build called, sorted
    unmeasured: tuple[str, ...] = ()  # projects with no script to build them

    def used_by(self, name: str) -> list[str]:
        return [slug for slug, parts in self.episodes.items() if name in parts]

    def unused(self, kind: str | None = None) -> list[str]:
        return sorted(e.name for e in registry.entries(kind) if not self.used_by(e.name))

    def to_dict(self) -> dict:
        parts = sorted(registry.entries(), key=lambda e: (e.kind, e.style, e.name))
        return {
            "schema": SCHEMA,
            "episodes": {slug: list(parts) for slug, parts in self.episodes.items()},
            "unmeasured": list(self.unmeasured),
            "parts": [
                {"name": e.name, "kind": e.kind, "style": e.style, "episodes": self.used_by(e.name)} for e in parts
            ],
        }

    def write(self, path: Path) -> Path:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return Path(path)

    @classmethod
    def read(cls, path: Path) -> Report:
        try:
            data = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise UsageError(f"{path}: {exc}") from None
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise UsageError(f"{path}: schema must be {SCHEMA}")
        if set(data) != {"schema", "episodes", "unmeasured", "parts"}:
            raise UsageError(f"{path}: fields must be schema, episodes, unmeasured, parts")
        episodes, unmeasured = data["episodes"], data["unmeasured"]
        if not isinstance(episodes, dict) or not all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(n, str) for n in v)
            for k, v in episodes.items()
        ):
            raise UsageError(f"{path}: episodes must map a slug to a list of part names")
        if not isinstance(unmeasured, list) or not all(isinstance(s, str) for s in unmeasured):
            raise UsageError(f"{path}: unmeasured must be a list of slugs")
        return cls({k: tuple(v) for k, v in episodes.items()}, tuple(unmeasured))


def discover(
    episodes: Path, packages: Path | None, scripts: Path, args: Mapping[str, Sequence[str]] | None = None
) -> tuple[list[Run], list[str]]:
    """A run per project folder in ``episodes`` and per ``<package>/project`` in ``packages`` whose script
    ``<slug with underscores>.py`` is in ``scripts`` (a project in both is built from ``episodes``); ``args`` adds
    command-line options by slug. Returns the runs by slug and the projects with no script."""
    projects: dict[str, Path] = {}
    if packages is not None and Path(packages).is_dir():
        for p in sorted(Path(packages).iterdir()):
            if (p / "project").is_dir():
                projects[_VERSION.sub("", p.name)] = p / "project"
    for p in sorted(Path(episodes).iterdir()):
        if p.is_dir():
            projects[p.name] = p
    runs, missing = [], []
    for slug in sorted(projects):
        script = Path(scripts) / f"{slug.replace('-', '_')}.py"
        if script.is_file():
            runs.append(Run(slug, script, projects[slug], tuple((args or {}).get(slug, ()))))
        else:
            missing.append(slug)
    return runs, missing


def measure(runs: Sequence[Run], work: Path, unmeasured: Sequence[str] = ()) -> Report:
    """Build each run on a copy of its project under ``work`` and report the parts each used."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    out: dict[str, tuple[str, ...]] = {}
    for run in runs:
        copy = work / run.slug
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(run.project, copy, symlinks=True)
        used = work / f"{run.slug}.used.json"
        try:
            probe(run.script, copy, run.args, used)
        except UsageError as exc:
            raise UsageError(f"{run.slug}: {exc}") from None
        out[run.slug] = tuple(json.loads(used.read_text()))
    return Report(out, tuple(unmeasured))


if __name__ == "__main__":  # the probe's child: python -m srstudio.usage SCRIPT PROJECT OUT [ARGS...]
    _probe_here(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[4:], Path(sys.argv[3]))
