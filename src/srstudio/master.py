"""Encode a reel's master and install it write-once (ADR 0170).

``scene-render encode --strict`` writes the master even when it exits on a finding, so a re-run of an encode whose
check fails used to leave a failed master where a good one had been. :func:`encode` (``srstudio master``) refuses
before the engine starts when a master already has the place, so a re-run spends nothing and replaces nothing. With
``next_name`` the new master goes beside the old one (``reel-v2.mp4``), and promoting it is an act of its own.

The engine encodes into a private stage inside the output folder, with ``--out-dir`` pointing at it, so every setting
of the document's outputs holds (``-o`` alone would encode an ad-hoc output with default settings instead). Each file
it writes is then installed at the same relative place under the real output folder with
:func:`srstudio.files.install_once`.

A ``--report PATH`` among the engine arguments is the caller's: a relative path is read from the caller's working
folder, not from the document's, where the engine runs (it used to land in ``<scene folder>/<PATH>``, the scene's
folder twice over). It is write-once like the master (ADR 0236): a report already at its place is refused before the
engine starts, or, with ``next_name``, the new one goes beside it (``render-report-v2.json``). The engine writes it
into a stage beside its place, and it is installed from there. A ``report=`` on the document's output is the
document's own and is written by the engine beside the document, as before.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import _stress_mix, files, gpu
from .errors import SrstudioError

__all__ = ["PLACES", "Encoded", "MasterError", "encode", "targets"]

PLACES = ("-o", "--path", "--out-dir")  # the engine arguments that choose where a master goes: this module's alone
REPORT = "--report"  # where the engine also writes each output's render report; {id} stands for the output's id
_TAIL = 1600  # characters of the engine's output kept for a message

Run = Callable[..., "subprocess.CompletedProcess[str]"]


class MasterError(SrstudioError, RuntimeError):
    """An encode that cannot be staged as asked, or an engine that wrote no master."""


@dataclass(frozen=True)
class Encoded:
    """Where the master (and any file beside it) was installed, the engine's exit status, which is 1 on a ``--strict``
    finding with the master kept all the same, the end of what the engine printed, and where the ``--report`` went."""

    paths: tuple[Path, ...]
    returncode: int
    output: str
    report: tuple[Path, ...] = ()  # where each render report asked for with --report was installed


def targets(scene: Path, out_dir: Path) -> list[Path]:
    """Where the outputs of the document ``scene`` land under ``out_dir``: each ``<output path=>``, which must be a
    relative path that stays inside it."""
    try:
        root = ET.fromstring(Path(scene).read_bytes())
    except (OSError, ET.ParseError) as e:
        raise MasterError(f"{scene}: not a scene document: {e}") from None
    places = [output.get("path", "") for output in root.iter("output")]
    if not places:
        raise MasterError(f"{Path(scene).name} declares no output to encode")
    found = []
    for place in places:
        relative = PurePosixPath(place)
        if not place or relative.is_absolute() or ".." in relative.parts:
            raise MasterError(f"{Path(scene).name}: output path {place!r} must be relative and stay in the out-dir")
        found.append(Path(out_dir) / relative)
    return found


def _refuse_places(args: Sequence[str]) -> None:
    for arg in args:
        if arg in PLACES or arg.startswith(tuple(f"{p}=" for p in PLACES if p.startswith("--"))):
            raise MasterError(f"{arg!r}: srstudio master chooses where the master goes; leave {', '.join(PLACES)} out")


@dataclass(frozen=True)
class _Report:
    """The ``--report`` in the engine arguments: the argument that holds it and where it goes, made absolute."""

    index: int
    joined: bool  # --report=PATH rather than --report PATH
    place: Path

    def places(self, scene: Path) -> list[Path]:
        """Each file the engine writes: one an output when the name holds ``{id}``."""
        if "{id}" not in self.place.name:
            return [self.place]
        ids = [output.get("id", "") for output in ET.fromstring(scene.read_bytes()).iter("output")]
        return [self.place.with_name(self.place.name.replace("{id}", i)) for i in ids]

    def staged(self, args: Sequence[str], stage: Path) -> list[str]:
        """``args`` with the report written into ``stage`` instead."""
        to = str(stage / self.place.name)
        return [*args[: self.index], f"{REPORT}={to}" if self.joined else to, *args[self.index + 1 :]]


def _report(args: Sequence[str]) -> _Report | None:
    """The ``--report`` among ``args``, a relative path read from the caller's working folder."""
    found = []
    for i, arg in enumerate(args):
        if arg == REPORT:
            found.append(_Report(i + 1, False, Path(args[i + 1]) if i + 1 < len(args) else Path()))
        elif arg.startswith(f"{REPORT}="):
            found.append(_Report(i, True, Path(arg.removeprefix(f"{REPORT}="))))
    if not found:
        return None
    if len(found) > 1:
        raise MasterError(f"{REPORT} is given {len(found)} times; give it once")
    report = found[0]
    if report.index >= len(args) or not str(args[report.index]).removeprefix(f"{REPORT}="):
        raise MasterError(f"{REPORT} needs a path to write the render report to")
    if "{id}" in str(report.place.parent):
        raise MasterError(f"{REPORT} {report.place}: {{id}} may stand only in the file name, not in a folder")
    return _Report(report.index, report.joined, Path(os.path.abspath(report.place)))


def _install(stage: Path, out_dir: Path, next_name: bool) -> tuple[list[Path], list[str]]:
    """Install each file under ``stage`` at its place under ``out_dir``. A place taken while the engine ran keeps what
    took it, and the new file goes to the next free name; the second list says so for each, for the error to name."""
    installed, displaced = [], []
    for made in sorted(p for p in stage.rglob("*") if p.is_file() or p.is_symlink()):
        place = out_dir / made.relative_to(stage)
        place.parent.mkdir(parents=True, exist_ok=True)
        if next_name:
            installed.append(files.install_next(made, place))
            continue
        try:
            installed.append(files.install_once(made, place))
        except files.WriteOnceError:
            kept = files.install_next(made, place)
            installed.append(kept)
            displaced.append(f"{place} appeared during the encode and was kept; the new file is {kept}")
    return installed, displaced


def encode(
    scene: str | os.PathLike[str],
    out_dir: str | os.PathLike[str],
    *,
    engine: str | os.PathLike[str],
    args: Sequence[str] = (),
    next_name: bool = False,
    run: Run = subprocess.run,
) -> Encoded:
    """Encode ``scene`` with ``engine`` and its extra ``args`` (``--strict``, ``--hw software``...), and install what
    it writes under ``out_dir``, the folder the document's output paths are relative to (``generated``).

    A ``--report`` in ``args`` is read from the working folder when relative, and is write-once like the master.

    Recorded named stress constrains integrated gain to measured true-peak headroom (ADR 0241); any lowered
    loudness target is reported in ``Encoded.output``. The authored scene is preserved.

    A place already taken, the master's or the report's, raises :class:`srstudio.files.WriteOnceError` before the
    engine starts, unless ``next_name``, which installs at the next free name. An engine that writes nothing raises
    :class:`MasterError`. The stages are removed whatever happens."""
    scene, out = Path(scene), Path(out_dir)
    _refuse_places(args)
    report = _report(args)
    places = targets(scene, out) + (report.places(scene) if report else [])
    taken = [p for p in places if os.path.lexists(p)]
    if taken and not next_name:
        raise files.WriteOnceError(
            f"{', '.join(map(str, taken))} exists: a master and its report are never replaced; encode with --next to"
            " write the new ones beside them, or move the old ones away by hand",
            code="files.exists",
            path=str(taken[0]),
        )
    out.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".master-", dir=out))
    report_stage = None
    try:
        if report:
            report.place.parent.mkdir(parents=True, exist_ok=True)
            report_stage = Path(tempfile.mkdtemp(prefix=".report-", dir=report.place.parent))
            args = report.staged(args, report_stage)
        command = [str(engine), "encode", scene.name, *args, "--out-dir", str(stage.resolve())]
        try:
            with gpu.held():  # the engine renders every frame on the GPU, --hw software included (ADR 0171)
                with _stress_mix.constrained(scene, out, str(engine), args, run) as (prepared, stress_note):
                    command[2] = prepared.name
                    done = run(command, cwd=scene.parent.resolve(), capture_output=True, text=True)
        except OSError as e:
            raise MasterError(f"cannot run the engine {engine}: {e}") from None
        said = (done.stdout + done.stderr + ("\n" + stress_note if stress_note else ""))[-_TAIL:]
        if not any(p.is_file() for p in stage.rglob("*")):
            raise MasterError(f"the engine wrote no master (exit {done.returncode}): {said}")
        installed, displaced = _install(stage, out, next_name)
        reported, late = _install(report_stage, report.place.parent, next_name) if report and report_stage else ([], [])
        if displaced or late:
            raise files.WriteOnceError("; ".join(displaced + late), code="files.exists", path=str(out))
        return Encoded(tuple(installed), done.returncode, said, tuple(reported))
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        if report_stage:
            shutil.rmtree(report_stage, ignore_errors=True)
