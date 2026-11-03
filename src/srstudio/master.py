"""Encode a reel's master and install it write-once (ADR 0170).

``scene-render encode --strict`` writes the master even when it exits on a finding, so a re-run of an encode whose
check fails used to leave a failed master where a good one had been. :func:`encode` (``srstudio master``) refuses
before the engine starts when a master already has the place, so a re-run spends nothing and replaces nothing. With
``next_name`` the new master goes beside the old one (``reel-v2.mp4``), and promoting it is an act of its own.

The engine encodes into a private stage inside the output folder, with ``--out-dir`` pointing at it, so every setting
of the document's outputs holds (``-o`` alone would encode an ad-hoc output with default settings instead). Each file
it writes is then installed at the same relative place under the real output folder with
:func:`srstudio.files.install_once`. The render report (``report=`` on the output, or ``--report``) is written by the
engine beside the document, as before: it is a measurement of the last encode, re-run each time.
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

from . import files, gpu
from .errors import SrstudioError

__all__ = ["PLACES", "Encoded", "MasterError", "encode", "targets"]

PLACES = ("-o", "--path", "--out-dir")  # the engine arguments that choose where a master goes: this module's alone
_TAIL = 1600  # characters of the engine's output kept for a message

Run = Callable[..., "subprocess.CompletedProcess[str]"]


class MasterError(SrstudioError, RuntimeError):
    """An encode that cannot be staged as asked, or an engine that wrote no master."""


@dataclass(frozen=True)
class Encoded:
    """Where the master (and any file beside it) was installed, the engine's exit status, which is 1 on a ``--strict``
    finding with the master kept all the same, and the end of what the engine printed."""

    paths: tuple[Path, ...]
    returncode: int
    output: str


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


def _install(stage: Path, out_dir: Path, next_name: bool) -> list[Path]:
    """Install each file under ``stage`` at its place under ``out_dir``. A place taken while the engine ran keeps what
    took it, and the new file goes to the next free name, which the raised error names."""
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
    if displaced:
        raise files.WriteOnceError("; ".join(displaced), code="files.exists", path=str(out_dir))
    return installed


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

    A place already taken raises :class:`srstudio.files.WriteOnceError` before the engine starts, unless
    ``next_name``, which installs at the next free name. An engine that writes nothing raises :class:`MasterError`. The
    stage is removed whatever happens."""
    scene, out = Path(scene), Path(out_dir)
    _refuse_places(args)
    places = targets(scene, out)
    taken = [p for p in places if os.path.lexists(p)]
    if taken and not next_name:
        raise files.WriteOnceError(
            f"{', '.join(map(str, taken))} exists: a master is never replaced; encode with --next to write the new one"
            " beside it, or move the old one away by hand",
            code="files.exists",
            path=str(taken[0]),
        )
    out.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".master-", dir=out))
    try:
        command = [str(engine), "encode", scene.name, *args, "--out-dir", str(stage.resolve())]
        try:
            with gpu.held():  # the engine renders every frame on the GPU, --hw software included (ADR 0171)
                done = run(command, cwd=scene.parent.resolve(), capture_output=True, text=True)
        except OSError as e:
            raise MasterError(f"cannot run the engine {engine}: {e}") from None
        said = (done.stdout + done.stderr)[-_TAIL:]
        if not any(p.is_file() for p in stage.rglob("*")):
            raise MasterError(f"the engine wrote no master (exit {done.returncode}): {said}")
        return Encoded(tuple(_install(stage, out, next_name)), done.returncode, said)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
