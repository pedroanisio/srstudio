#!/usr/bin/env python3
"""Write a 3D location's shots and blocking as one record srstudio reads (ADR 0179).

Run it with srlocations' interpreter, isolated, since srstudio's cannot import srlocations:

    /home/pals/src/studio/.venv/bin/python -I tools/location_export.py --repo /home/pals/src/studio \\
        --location airliner --shot down-the-aisle --shot window-seat --size 1080x1920 --out RECORD.json
    ... --module economy_row.py --shot ...   # a location module: NAME, VERSION and location() -> Location

It never runs srlocations from a checkout. It writes the pinned commit's ``srlocations/`` and ``catalog/`` from the
repository's object store to ``generated/srlocations/<commit>`` (folders 700, files 600), checks every file there
against that commit's tree by its git blob id before each run, imports srlocations from there and nowhere else, and
refuses when anything differs: an edited, extra or missing file, a module loaded from elsewhere, an srlocations plugin
or extra catalog in the environment. The record is read back through ``srstudio.location_bridge``, loaded by path,
before it is written, so the exporter writes nothing srstudio would refuse.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BRIDGE = REPO / "src" / "srstudio" / "location_bridge.py"
EXPORTED = ("srlocations", "catalog")  # what of the commit the exporter runs: the package and its catalog
BLOCKING_KEYS = {  # srlocations.framing.blocking's keys at the pin, and the record's name for each
    "mark": "mark",
    "at": "at_m",
    "facing": "facing_deg",
    "framing": "framing",
    "height": "height_m",
    "feet": "feet_px",
    "head": "head_px",
    "scale": "pixels_per_metre",
    "in_frame": "in_frame",
}
SIZE = re.compile(r"([1-9]\d{0,4})x([1-9]\d{0,4})")


class ExportError(RuntimeError):
    """The exporter cannot prove what it ran, or what srlocations gave it is not what the record holds."""


def git(repo: Path, *words: str) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *words], capture_output=True, check=False)
    if done.returncode:
        raise ExportError(f"git {' '.join(words)} failed in {repo}: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout


def blob_id(data: bytes) -> str:
    """The id git gives a file of these bytes (SHA-1 object format)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def require_commit(repo: Path, commit: str) -> str:
    """``commit`` as the repository has it; refused when the repository does not hold it."""
    done = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "-q", f"{commit}^{{commit}}"], capture_output=True, text=True
    )
    if done.returncode or done.stdout.strip() != commit:
        raise ExportError(f"{repo} does not hold srlocations commit {commit}, the pinned one: fetch it first")
    return commit


def tree(repo: Path, commit: str) -> dict[str, str]:
    """Every file of ``EXPORTED`` at ``commit``, by path, with its blob id. A link or a submodule is refused: an export
    holds plain files only."""
    listing: dict[str, str] = {}
    for line in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", *EXPORTED).split(b"\0"):
        if not line:
            continue
        meta, path = line.decode().split("\t", 1)
        mode, kind, blob = meta.split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ExportError(f"{path} at {commit} is a {kind} of mode {mode}; an export holds plain files only")
        listing[path] = blob
    if not listing:
        raise ExportError(f"{commit} holds none of {', '.join(EXPORTED)}")
    return listing


def verify(dest: Path, listing: Mapping[str, str], commit: str) -> None:
    """``dest`` holds exactly the files of ``listing``, each with its blob id, and no other file or folder."""
    entries = list(dest.rglob("*"))
    folders = {str(p.relative_to(dest)) for p in entries if p.is_dir() and not p.is_symlink()}
    files = {str(p.relative_to(dest)) for p in entries} - folders
    wanted = {str(Path(path).parent) for path in listing}
    wanted |= {str(parent) for path in wanted for parent in Path(path).parents if str(parent) != "."}
    problems = [f"missing {p}" for p in sorted(set(listing) - files)]
    problems += [f"extra {p}" for p in sorted(files - set(listing))]
    problems += [f"extra folder {p}" for p in sorted(folders - wanted)]
    problems += [
        f"changed {p}"
        for p in sorted(set(listing) & files)
        if (dest / p).is_symlink() or blob_id((dest / p).read_bytes()) != listing[p]
    ]
    if problems:
        found = "; ".join(problems[:8])
        raise ExportError(f"{dest} differs from srlocations {commit}: {found}. Remove it to export the commit again")


def export(repo: Path, commit: str, dest: Path) -> Path:
    """The pinned files at ``dest``: written from the object store when absent, checked file by file either way."""
    listing = tree(repo, commit)
    if not dest.exists():
        dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        building = Path(tempfile.mkdtemp(prefix=f".{dest.name}.", dir=dest.parent))
        try:
            for path, blob in listing.items():
                target = building / path
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(handle, "wb") as out:
                    out.write(git(repo, "cat-file", "blob", blob))
            for folder in [building, *building.rglob("*")]:
                if folder.is_dir():
                    folder.chmod(0o700)
            building.rename(dest)
        except BaseException:
            shutil.rmtree(building, ignore_errors=True)
            raise
    verify(dest, listing, commit)
    return dest


def check_loaded(modules: Mapping[str, Any], root: Path) -> None:
    """Every srlocations module in ``modules`` was loaded from under ``root``."""
    root = root.resolve()
    for name, module in sorted(modules.items()):
        if name != "srlocations" and not name.startswith("srlocations."):
            continue
        source = getattr(module, "__file__", None)
        if source is None or not Path(source).resolve().is_relative_to(root):
            raise ExportError(f"{name} was loaded from {source}, not from the pinned export at {root}")


def mark_record(blocked: Mapping[str, Any]) -> dict[str, Any]:
    """One mark of srlocations' blocking under the record's names; another set of keys is refused."""
    if set(blocked) != set(BLOCKING_KEYS):
        raise ExportError(f"srlocations' blocking gave keys {sorted(blocked)}; the record maps {sorted(BLOCKING_KEYS)}")
    return {BLOCKING_KEYS[key]: value for key, value in blocked.items()}


def camera_record(shot: Any, view: Any, width: int, height: int) -> dict[str, Any]:
    """A shot's camera as srlocations' ``compiler.Projection`` holds it: the basis's columns are the camera's axes,
    and the side of the frame the gate fits to is read from the focal length it computed."""
    gate = [float(v) for v in view.SENSOR]
    fits = {"width": shot.lens * width / gate[0], "height": shot.lens * height / gate[1]}
    fit = next((side for side, focal in fits.items() if math.isclose(view.focal, focal, rel_tol=1e-12)), None)
    if fit is None:
        raise ExportError(f"a focal length of {view.focal} px fits neither side of a {width}x{height} frame")
    column = [[float(view.basis[row][c]) for row in range(3)] for c in range(3)]
    return {
        "eye_m": [float(v) for v in shot.eye],
        "look_at_m": [float(v) for v in shot.look_at],
        "lens_mm": float(shot.lens),
        "gate_mm": gate,
        "fit": fit,
        "focal_px": float(view.focal),
        "near_m": float(view.NEAR),
        "right": column[0],
        "up": column[1],
        "forward": column[2],
    }


def write(record: dict[str, Any], out: Path, bridge: ModuleType) -> Path:
    """``record`` as JSON at ``out`` (folder 700, file 600), after ``bridge.from_data`` reads it."""
    bridge.from_data(json.loads(json.dumps(record, allow_nan=False)))
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = json.dumps(record, indent=1, sort_keys=True, allow_nan=False) + "\n"
    handle, partial = tempfile.mkstemp(prefix=f".{out.name}.", dir=out.parent)
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(text)
        os.chmod(partial, 0o600)
        os.replace(partial, out)
    except BaseException:
        Path(partial).unlink(missing_ok=True)
        raise
    return out


def size(text: str) -> tuple[int, int]:
    found = SIZE.fullmatch(text)
    if not found:
        raise ExportError(f"a frame size is WIDTHxHEIGHT in pixels, such as 1080x1920, not {text!r}")
    return int(found.group(1)), int(found.group(2))


def load_bridge() -> ModuleType:
    """srstudio's reader, by path: srstudio's package needs its own interpreter, this one module needs none."""
    found = importlib.util.spec_from_file_location("srstudio_location_bridge", BRIDGE)
    if found is None or found.loader is None:
        raise ExportError(f"cannot load {BRIDGE}")
    module = importlib.util.module_from_spec(found)
    sys.modules[found.name] = module
    found.loader.exec_module(module)
    return module


def workspace_generated() -> Path:
    """The workspace's generated/ folder, as tools/gate.sh finds it: beside the repository's shared git folder."""
    common = Path(git(REPO, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())
    return common.parent.parent / "generated"


def _module_location(path: Path, bridge: ModuleType) -> tuple[Any, dict[str, Any]]:
    from srlocations.location import Location

    found = importlib.util.spec_from_file_location(f"srlocations_location_{path.stem}", path)
    if found is None or found.loader is None:
        raise ExportError(f"cannot load the location module {path}")
    module = importlib.util.module_from_spec(found)
    found.loader.exec_module(module)
    name, version = getattr(module, "NAME", None), getattr(module, "VERSION", None)
    if not isinstance(name, str) or not bridge.ITEM.fullmatch(name):
        raise ExportError(f"{path} names its location in NAME, as a catalog item is named, not {name!r}")
    if not isinstance(version, str) or not bridge.SEMVER.fullmatch(version):
        raise ExportError(f"{path} versions its location in VERSION, major.minor.patch, not {version!r}")
    location = module.location()
    if not isinstance(location, Location):
        raise ExportError(f"{path}: location() gave a {type(location).__name__}, not an srlocations Location")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return location, {"source": "module", "name": name, "version": version, "digest": digest}


def _catalog_location(root: Path, wanted: str) -> tuple[Any, dict[str, Any]]:
    from srlocations.catalog import SharedCatalog
    from srlocations.registry import CatalogError

    name, _, version = wanted.partition("@")
    try:
        catalog = SharedCatalog.open(root)
        entry = catalog.get("location", name, version or None)  # refuses a file that no longer matches its digest
        location = catalog.location(entry.name, entry.version)
    except CatalogError as error:
        raise ExportError(f"the pinned catalog refuses {wanted!r}: {error}") from None
    source = {"source": "catalog", "catalog": catalog.name, "name": entry.name, "version": entry.version}
    return location, {**source, "digest": entry.digest}


def run(args: argparse.Namespace, bridge: ModuleType) -> Path:
    width, height = size(args.size)
    commit = require_commit(args.repo.resolve(), bridge.SRLOCATIONS_COMMIT)
    if os.environ.get("SRLOCATIONS_CATALOGS"):
        raise ExportError("SRLOCATIONS_CATALOGS is set: a record is built from the pinned catalog alone; unset it")
    if importlib.metadata.entry_points(group="srlocations.plugins"):
        raise ExportError("this interpreter installs srlocations plugins: a record is built from the stock library")
    if any(name == "srlocations" or name.startswith("srlocations.") for name in sys.modules):
        raise ExportError("srlocations was imported before the exporter chose where from")
    root = export(args.repo.resolve(), commit, (args.export_root or workspace_generated() / "srlocations") / commit)
    sys.dont_write_bytecode = True  # an import must leave the export as the commit has it
    sys.path.insert(0, str(root))
    from srlocations.compiler import Projection
    from srlocations.framing import blocking

    if args.module:
        location, source = _module_location(args.module.resolve(), bridge)
    else:
        location, source = _catalog_location(root / "catalog", args.location)
    shots = []
    for name in args.shot:
        if name not in location.shots:
            raise ExportError(f"{source['name']} has no shot {name!r}; it has {', '.join(sorted(location.shots))}")
        take = location.shots[name]
        camera = camera_record(take, Projection(take, width, height), width, height)
        marks = [mark_record(item) for item in blocking(location, name, width, height)]
        shots.append({"name": name, "camera": camera, "marks": marks})
    check_loaded(sys.modules, root)
    verify(root, tree(args.repo.resolve(), commit), commit)  # nothing changed the export while it ran
    record = {
        "schema_version": bridge.SCHEMA_VERSION,
        "srlocations_commit": commit,
        "location": source,
        "frame": {"width_px": width, "height_px": height},
        "shots": shots,
    }
    return write(record, args.out, bridge)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--repo", type=Path, required=True, help="an srlocations git repository holding the pin")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--location", help="a catalog location, NAME or NAME@VERSION (the newest when no version)")
    which.add_argument("--module", type=Path, help="a location module: NAME, VERSION and location() -> Location")
    parser.add_argument("--shot", action="append", required=True, help="a shot to record; repeat for more")
    parser.add_argument("--size", required=True, help="the frame, WIDTHxHEIGHT in pixels: 1080x1920 for a reel")
    parser.add_argument("--out", type=Path, required=True, help="the record to write")
    parser.add_argument(
        "--export-root", type=Path, help="where pinned exports go (the workspace's generated/srlocations)"
    )
    args = parser.parse_args(argv)
    bridge = load_bridge()
    try:
        out = run(args, bridge)
    except (ExportError, bridge.LocationBridgeError) as error:
        print(f"location_export: {error}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
