"""Which registered parts each episode uses, measured from the calls its build makes.

Hand-written declarations of the episodes that use a part drift as episodes are added (ADR 0017, ADR 0032).
:func:`trace` records instead every registered builder that runs: it matches the code objects of each builder (a
function, or the methods a class part defines itself) under a profiler hook, so a call counts however it is
reached (a module attribute, an imported name, the registry, or another part drawing it). A character moving its
head is drawn by :func:`srstudio.toon_head.figure` from its rig, so that call counts for the part the rig belongs to.
:func:`measure` runs each
episode script on a copy of its project in a fresh interpreter (:func:`probe`) and gathers a :class:`Report`: the
parts each episode used, and with the registry, the parts no episode uses. ``srstudio usage`` writes it as JSON.
"""

from __future__ import annotations

import inspect
import json
import operator
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

from . import parts, registry, releases, toon_head, toon_rigs
from .errors import SrstudioError

SCHEMA = "1.0.0"
_VERSION = re.compile(r"-\d+\.\d+\.\d+\Z")


class UsageError(SrstudioError, RuntimeError):
    """An episode that failed to build, or a usage file that cannot be read."""


def _cells(func) -> tuple[object, ...]:
    """The values a closure closed over, in its code's ``co_freevars`` order (empty for a plain function)."""
    return tuple(cell.cell_contents for cell in func.__closure__ or ())


def _codes() -> dict[CodeType, list[tuple[str, tuple[object, ...]]]]:
    """Each builder's code object, with the part it draws and the values it closed over: parts made by one factory
    (one closure per look) share a code object, and only those values tell them apart."""
    codes: dict[CodeType, list[tuple[str, tuple[object, ...]]]] = {}
    for entry in registry.entries():
        b = entry.builder
        if inspect.isclass(b):
            for value in vars(b).values():
                func = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
                if inspect.isfunction(func):
                    codes.setdefault(func.__code__, []).append((entry.name, ()))
        elif inspect.isfunction(b):
            codes.setdefault(b.__code__, []).append((entry.name, _cells(b)))
    return codes


def _called(frame, parts: Sequence[tuple[str, tuple[object, ...]]]) -> str | None:
    """The part a call into a builder's code draws: the only one with that code, or the one whose closed-over values
    are the frame's own."""
    if len(parts) == 1:
        return parts[0][0]
    values = tuple(frame.f_locals.get(name) for name in frame.f_code.co_freevars)
    return next(
        (name for name, cells in parts if len(cells) == len(values) and all(map(operator.is_, cells, values))), None
    )


@contextmanager
def trace() -> Iterator[set[str]]:
    """The names of the registered parts called inside the block (the set fills as they run)."""
    codes, used = _codes(), set()
    rigged = {id(rig): name for name, rig in toon_rigs.RIGS.items()}
    previous = sys.getprofile()

    def hook(frame, event, arg):
        if event == "call":
            parts = codes.get(frame.f_code)
            name = _called(frame, parts) if parts else None
            if frame.f_code is toon_head.figure.__code__:
                name = rigged.get(id(frame.f_locals["rig"]))
            if name is not None:
                used.add(name)

    sys.setprofile(hook)
    try:
        yield used
    finally:
        sys.setprofile(previous)


@contextmanager
def recorded(project: Path) -> Iterator[None]:
    """Trace the build in the block and leave what it drew in ``project``, for the delivery gate
    (:func:`srstudio.parts.write_record`). A build that fails leaves no record: an older one would no longer say what
    the project holds."""
    (Path(project) / parts.RECORD).unlink(missing_ok=True)
    with trace() as used:
        try:
            yield
        except SystemExit as stop:
            if stop.code in (None, 0):
                parts.write_record(project, parts.drawn(used))
            raise
        parts.write_record(project, parts.drawn(used))


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
    unmeasured: tuple[str, ...] = ()  # projects with no script to build them, or skipped on request

    def used_by(self, name: str) -> list[str]:
        return [slug for slug, parts in self.episodes.items() if name in parts]

    def unused(self, kind: str | None = None) -> list[str]:
        return sorted(e.name for e in registry.entries(kind) if not self.used_by(e.name))

    def pin_drift(self, pinned: Mapping[str, releases.Release]) -> list[str]:
        """Each measured part a release does not pin at the version it drew (ADR 0047)."""
        table = parts.load()
        built = {release.builder_name: release for release in pinned.values()}  # a project can differ from its slug
        drift = []
        for slug, used in self.episodes.items():
            release = pinned.get(slug) or built.get(slug.replace("-", "_"))
            if release is None:
                continue
            pins = release.parts or {}
            for part in sorted(used):
                name, _, number = part.partition("@")
                if name not in table:
                    continue
                drawn = int(number or 1)
                if name not in pins:
                    drift.append(f"{slug}: draws {name} version {drawn} but pins nothing for it")
                elif pins[name] != drawn:
                    drift.append(f"{slug}: draws {name} version {drawn} but pins version {pins[name]}")
        return drift

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
    episodes: Path,
    packages: Path | None,
    scripts: Path,
    args: Mapping[str, Sequence[str]] | None = None,
    skip: Sequence[str] = (),
) -> tuple[list[Run], list[str]]:
    """A run per project folder in ``episodes`` and per ``<package>/project`` in ``packages`` whose script
    ``<slug with underscores>.py`` is in ``scripts`` (or the builder its release in ``<scripts>/posts`` names, see
    :mod:`srstudio.releases`; a project in both is built from ``episodes``); ``args`` adds
    command-line options by slug, and ``skip`` names projects not to build (one still in progress, whose build
    cannot run yet). Returns the runs by slug and the projects not measured: those with no script and those
    skipped. A skipped slug, or one given ``args``, that names no project raises :class:`UsageError`."""
    projects: dict[str, Path] = {}
    if packages is not None and Path(packages).is_dir():
        for p in sorted(Path(packages).iterdir()):
            if (p / "project").is_dir():
                projects[_VERSION.sub("", p.name)] = p / "project"
    for p in sorted(Path(episodes).iterdir()):
        if p.is_dir():
            projects[p.name] = p
    unknown = sorted(set(skip) - set(projects))
    if unknown:
        raise UsageError(f"--skip names no project: {', '.join(unknown)}")
    unknown = sorted(set(args or {}) - set(projects))
    if unknown:
        raise UsageError(f"--arg names no project: {', '.join(unknown)}")
    builders: dict[str, str] = {}
    if (Path(scripts) / "posts" / "__init__.py").is_file():
        try:
            builders = {slug: r.builder_name for slug, r in releases.load(Path(scripts) / "posts").items()}
        except releases.ReleaseError as exc:
            raise UsageError(f"the releases in {scripts}/posts cannot be read: {exc}") from exc
    runs, missing = [], []
    for slug in sorted(projects):
        if slug in skip:
            missing.append(slug)
            continue
        script = Path(scripts) / f"{builders.get(slug, slug.replace('-', '_'))}.py"
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
