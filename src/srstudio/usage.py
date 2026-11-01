"""Which registered parts each episode uses, measured from the calls its build makes.

Hand-written declarations of the episodes that use a part drift as episodes are added (ADR 0017, ADR 0032).
:func:`trace` consumes explicit registered-builder and performer scopes. Function
builders retain their signatures; class builders keep their identity and emit from
class-owned methods. Shared performers identify the part and version they draw.
Head rigs and Canvas ID allocation use the same event stream. Tracing leaves an
existing profiler untouched and needs neither Python source nor frame-local names.
:func:`measure` runs each
episode script on a copy of its project in a fresh interpreter (:func:`probe`) and gathers a :class:`Report`: the
parts each episode used, and with the registry, the parts no episode uses. ``srstudio usage`` writes it as JSON.
"""

from __future__ import annotations

import json
import os
import re
import runpy
import shutil
import subprocess
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from . import anatomy_ledger, drawing_events, figure_record, parts, registry, releases, toon_rigs
from .errors import SrstudioError

SCHEMA = "1.0.0"
_VERSION = re.compile(r"-\d+\.\d+\.\d+\Z")


class UsageError(SrstudioError, RuntimeError):
    """An episode that failed to build, or a usage file that cannot be read."""


@contextmanager
def trace(figures: list[figure_record.Figure] | None = None) -> Iterator[set[str]]:
    """Observe explicit builder and rig scopes, retaining outermost character IDs.

    Nested traces each receive the events. An existing profiler remains installed
    and continues receiving calls; neither source files nor stack frames are read.
    Failed scopes still report attempted usage, while recorded() refuses failed builds.
    """
    entries = tuple(registry.entries())
    used: set[str] = set()
    builders: dict[int, str] = {}
    for entry in entries:
        builders.setdefault(id(entry.builder), entry.name)
    rigged = {id(rig): name for name, rig in toon_rigs.RIGS.items()}
    characters = {entry.name for entry in entries if entry.kind == 'character'} | set(rigged.values())
    names = {entry.name for entry in entries}
    drawing_state: ContextVar[tuple[object, str, list[str]] | None] = ContextVar('srstudio_usage_figure', default=None)

    def event(event: drawing_events.DrawEvent) -> None:
        drawing = drawing_state.get()
        name: str | None
        if event.kind == 'begin':
            if isinstance(event.subject, str):
                if event.subject not in names:
                    raise UsageError(f'no registered drawing named {event.subject!r}')
                name = event.subject
            else:
                name = builders.get(id(event.subject)) or rigged.get(id(event.subject))
            if name is not None:
                used.add(name)
                if figures is not None and drawing is None and name in characters:
                    drawing_state.set((event.token, name, []))
        elif drawing is not None:
            if event.kind == 'id' and event.identifier is not None:
                drawing[2].append(event.identifier)
            elif event.kind == 'end' and drawing[0] is event.token:
                if drawing[2] and figures is not None:
                    figures.append(figure_record.Figure(drawing[1], tuple(drawing[2])))
                drawing_state.set(None)

    with drawing_events.observe(event):
        yield used


@contextmanager
def recorded(project: Path) -> Iterator[None]:
    """Trace the build in the block and leave what it drew in ``project``, for the delivery gates
    (:func:`srstudio.parts.write_record`, :func:`srstudio.figure_record.write`, :func:`srstudio.anatomy_ledger.write`).
    A build that fails leaves no record: an older one would no longer say what the project holds."""
    (Path(project) / parts.RECORD).unlink(missing_ok=True)
    (Path(project) / figure_record.RECORD).unlink(missing_ok=True)
    (Path(project) / anatomy_ledger.RECORD).unlink(missing_ok=True)
    figures: list[figure_record.Figure] = []

    def write(used: set[str]) -> None:
        parts.write_record(project, parts.drawn(used))
        figure_record.write(project, figures)
        anatomy_ledger.write(project, noted)

    with trace(figures) as used, anatomy_ledger.recording() as noted:
        try:
            yield
        except SystemExit as stop:
            if stop.code in (None, 0):
                write(used)
            raise
        write(used)


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
    unmeasured: tuple[str, ...] = ()  # projects with no script, skipped on request, or whose build failed
    failures: Mapping[str, str] = field(default_factory=dict, compare=False)  # why each build failed; not stored

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


PILOTS = "pilots"  # the folder of series, in the projects and in the scripts, that the library holds apart


def pilot_projects(episodes: Path) -> dict[str, tuple[str, Path]]:
    """The pilot projects under ``<episodes>/pilots/<series>/<slug>``, as ``{slug: (series, folder)}`` in slug order
    (ADR 0054: a pilot is for a future channel, so it sits beside the library's projects and not among them)."""
    found: dict[str, tuple[str, Path]] = {}
    root = Path(episodes) / PILOTS
    for series in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else ():
        for project in sorted(p for p in series.iterdir() if p.is_dir()):
            found[project.name] = (series.name, project)
    return dict(sorted(found.items()))


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
    cannot run yet). A project with a ``voiced/`` recording whose script takes ``--voice`` is built from it: its
    delivered master was, and its silent ``script.json`` can be an older timing that the silent build refuses.
    Returns the runs by slug and the projects not measured: those with no script and those
    skipped. A skipped slug, or one given ``args``, that names no project raises :class:`UsageError`."""
    projects: dict[str, Path] = {}
    if packages is not None and Path(packages).is_dir():
        for p in sorted(Path(packages).iterdir()):
            if (p / "project").is_dir():
                projects[_VERSION.sub("", p.name)] = p / "project"
    for p in sorted(Path(episodes).iterdir()):
        if p.is_dir() and p.name != PILOTS:
            projects[p.name] = p
    pilots = pilot_projects(episodes)
    clash = sorted(set(pilots) & set(projects))
    if clash:
        raise UsageError(f"a pilot takes the slug of a library project: {', '.join(clash)}")
    projects.update({slug: folder for slug, (_, folder) in pilots.items()})
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
        home = Path(scripts) / PILOTS if slug in pilots else Path(scripts)
        script = home / f"{builders.get(slug, slug.replace('-', '_'))}.py"
        if script.is_file():
            given = tuple((args or {}).get(slug, ()))
            if "--voice" not in given and (projects[slug] / "voiced").is_dir() and "--voice" in script.read_text():
                given = (*given, "--voice")
            runs.append(Run(slug, script, projects[slug], given))
        else:
            missing.append(slug)
    return runs, missing


def measure(runs: Sequence[Run], work: Path, unmeasured: Sequence[str] = ()) -> Report:
    """Build each run on a copy of its project under ``work`` and report the parts each used. A build that fails is
    reported as not measured, with its reason in ``failures``, and the others still run: one episode that cannot build
    must not leave every other part's usage stale. When no build succeeds nothing is reported, since an environment
    that cannot build at all must not replace a good report with an empty one."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    out: dict[str, tuple[str, ...]] = {}
    failures: dict[str, str] = {}
    for run in runs:
        copy = work / run.slug
        if copy.exists():
            shutil.rmtree(copy)
        shutil.copytree(run.project, copy, symlinks=True)
        used = work / f"{run.slug}.used.json"
        try:
            probe(run.script, copy, run.args, used)
        except UsageError as exc:
            failures[run.slug] = str(exc)
            continue
        out[run.slug] = tuple(json.loads(used.read_text()))
    if runs and not out:
        raise UsageError(
            f"every episode failed to build: {', '.join(failures)}; the first: {next(iter(failures.values()))}"
        )
    return Report(out, (*unmeasured, *failures), failures)


if __name__ == "__main__":  # the probe's child: python -m srstudio.usage SCRIPT PROJECT OUT [ARGS...]
    _probe_here(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[4:], Path(sys.argv[3]))
