#!/usr/bin/env python3
"""Write a 3D location's shots and blocking as one record srstudio reads (ADR 0179).

Run it with srlocations' interpreter, isolated, since srstudio's cannot import srlocations:

    /home/pals/src/studio/.venv/bin/python -I tools/location_export.py --repo /home/pals/src/studio \\
        --location airliner --shot down-the-aisle --shot window-seat --size 1080x1920 --out RECORD.json
    ... --module economy_row.py --shot ...   # a location module: NAME, VERSION and location() -> Location
    ... --blocking REQUEST.json              # and a mannequin posed on marks, checked against the set (ADR 0184)

It never runs srlocations from a checkout. It writes the pinned commit's ``srlocations/`` and ``catalog/`` from the
repository's object store to ``generated/srlocations/<commit>`` (folders 700, files 600), checks every file there
against that commit's tree by its git blob id before each run, imports srlocations from there and nowhere else, and
refuses when anything differs: an edited, extra or missing file, a module loaded from elsewhere, an srlocations plugin
or extra catalog in the environment. The record is read back through ``srstudio.location_bridge``, loaded by path,
before it is written, so the exporter writes nothing srstudio would refuse.

With ``--blocking``, a request ``location_bridge.parse_request`` reads, srlocations' stock mannequin stands or sits on
each mark it names (``Location.stand``, which settles a sitter on the set's seat beside the mark), looks and reaches
at named points, and is measured: its joints, sight and seat, the limbs that pass through the set
(``Location.faults``) or through each other (``tangled``), how far each limb that should carry it is from the set and
which part is there (``gap``), the controls stopped at their ranges, and its full pose. A reach is not refused for
passing through the set: the record says so, and ``LocationRecord.require_clear`` refuses it in srstudio.
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
from collections.abc import Collection, Mapping, Sequence
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
TANGLED = re.compile(r"([a-z][a-z0-9_]*) passes through ([a-z][a-z0-9_]*)")  # mannequin.tangled()'s lines


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
    blocked = None
    if args.blocking:  # after the marks are recorded: a body on a mark changes what framing.blocking reports
        request = bridge.parse_request(read_request(args.blocking, bridge))
        blocked = block(location, request, args.shot, width, height, bridge)
    check_loaded(sys.modules, root)
    verify(root, tree(args.repo.resolve(), commit), commit)  # nothing changed the export while it ran
    record = {
        "schema_version": bridge.SCHEMA_WITHOUT_BLOCKING if blocked is None else bridge.SCHEMA_VERSION,
        "srlocations_commit": commit,
        "location": source,
        "frame": {"width_px": width, "height_px": height},
        "shots": shots,
        **({} if blocked is None else {"blocking": blocked}),
    }
    return write(record, args.out, bridge)


def read_request(path: Path, bridge: ModuleType) -> bytes:
    try:
        with open(path, "rb") as handle:
            return handle.read(bridge.MAX_BYTES + 1)
    except OSError as error:
        raise ExportError(f"cannot read the blocking request {path}: {error}") from None


def pixel(view: Any, point: Any) -> list[float] | None:
    """Where srlocations' projection puts a world point, or None behind the camera."""
    found = view.pixel(point)
    return None if found is None else [float(v) for v in found]


def limb_of(path: str) -> str:
    """The joint a figure's leaf belongs to: ``bench/left_hand.ball`` is the left hand's."""
    return path.rpartition("/")[2].partition(".")[0]


def tangles(lines: Sequence[str]) -> list[dict[str, str]]:
    """srlocations' ``tangled()`` lines as pairs of limbs; a line of another shape is refused, not guessed at."""
    pairs = []
    for line in lines:
        found = TANGLED.fullmatch(line)
        if not found:
            raise ExportError(f"srlocations reported a tangle as {line!r}; the record reads 'LIMB passes through LIMB'")
        pairs.append({"limb": found.group(1), "other": found.group(2)})
    return pairs


def at_limits(values: Mapping[str, float], ranges: Mapping[str, Any], moves: Collection[str]) -> list[dict[str, Any]]:
    """The turning controls of a pose stopped at an end of their range; the hips' moves are in metres and left out."""
    hits = []
    for key, value in sorted(values.items()):
        dof = ranges[key]
        if dof.turn in moves:
            continue
        for bound, end in (("low", dof.low), ("high", dof.high)):
            if math.isclose(value, end, rel_tol=0.0, abs_tol=1e-9):
                hits.append({"control": key, "value_deg": float(value), "bound": bound, "bound_deg": float(end)})
    return hits


def block(location: Any, request: Any, shot_names: Sequence[str], width: int, height: int, bridge: ModuleType) -> dict:
    """The record's blocking section: every figure of ``request`` posed on its mark, then measured."""
    from srlocations.collision import GAP, Body, deepest
    from srlocations.compiler import Projection
    from srlocations.geometry import Transform, Vec3
    from srlocations.registry import CatalogError
    from srlocations.stock.mannequin import JOINTS, MOVES, PARAMETERS, Pose

    framed = dict(location.shots)
    points = {name: Vec3(*at) for name, at in request.points.items()}
    figures = {}
    for item in request.figures:
        if item.mark not in location.marks:
            raise ExportError(
                f"the request poses a figure on {item.mark!r}; the location has {', '.join(location.marks)}"
            )
        body = {"kind": item.kind, "seed": item.seed, "height": item.height_m}
        try:
            (figure,) = location.stand(
                item.mark, pose=item.pose, adjust=dict(item.adjust), **{k: v for k, v in body.items() if v is not None}
            )
        except (ValueError, CatalogError) as error:  # PoseError and CollisionError are ValueErrors
            raise ExportError(f"srlocations cannot {item.posture} a body on {item.mark!r}: {error}") from None
        if figure.sits != (item.posture == "sit"):
            raise ExportError(
                f"the pose {item.pose!r} {'sits' if figure.sits else 'stands'}; the request asks to {item.posture}"
            )
        if figure.sits and location.seat_of(figure) is None:
            raise ExportError(
                f"no seat of {location.name} is within reach of mark {item.mark!r}, so nothing sits there"
            )
        figures[item.mark] = figure
    for item in request.figures:
        figure = figures[item.mark]
        if item.look_at is not None:
            figure.look_at(points[item.look_at])
        for reach in item.reach:
            pole = None if reach.pole is None else points[reach.pole]
            try:
                figure.reach_to(reach.joint, points[reach.to], bridge.REACH_TOLERANCE_M, pole)
            except ValueError as error:
                raise ExportError(f"the body on {item.mark!r} cannot reach {reach.to!r}: {error}") from None
    if dict(location.shots) != framed:
        raise ExportError("standing bodies on the marks moved a shot that follows a figure; record it without them")
    contact, standing = location.contact, location._set()
    parts = sorted({piece.path for found in standing for piece in found.hulls})

    def facing(yaw: float) -> float:
        ahead = Transform.at(yaw=yaw).apply((0, 0, 1))  # as framing.blocking turns a mark's facing into degrees
        return math.degrees(math.atan2(ahead.x, ahead.z))

    def support(figure: Any, joint: str, way: Any, name: str) -> dict[str, Any]:
        gap = location.gap(figure, joint, way)
        part = None
        if gap < GAP:  # what gap() met: the deepest piece the limb, moved that far, touches
            limb = Body.of(figure, contact).part(lambda path: path.rpartition("/")[2] == joint)
            met = [
                hit
                for hit in (deepest(limb, other, Vec3(way.x * gap, way.y * gap, way.z * gap)) for other in standing)
                if hit
            ]
            if not met:
                raise ExportError(f"srlocations' gap() met the set {gap} m {name} of {joint}, and nothing is there")
            part = max(met, key=lambda hit: hit.depth).second
        return {"joint": joint, "way": name, "gap_m": float(gap), "part": part, "rests": gap <= contact.rest}

    out = []
    for item in request.figures:
        figure = figures[item.mark]
        frames = figure.frames()
        joints = {name: figure.transform.then(frames[name]).position for name in bridge.BODY_JOINTS}
        eye, ahead = figure.sight()
        seat = location.seat_of(figure)
        held = [support(figure, joint, Vec3(0, -1, 0), "down") for joint in figure.footing()]
        if seat is not None and seat.back:
            behind = Transform.at(yaw=seat.facing).apply((0, 0, -1))  # as review._resting measures a backrest
            held += [support(figure, joint, behind, "back") for joint in figure.backing()]
        under = next((s["part"] for s in held if s["joint"] == "hips" and s["way"] == "down"), None)
        backs = [s["rests"] for s in held if s["way"] == "back"]
        values = figure.values()
        at = Vec3.of(figure.at)
        mark = location.marks[item.mark].at
        pixels = []
        for name in shot_names:
            view = Projection(location.shots[name], width, height)
            top = None if seat is None else seat.at + Vec3(0, seat.height, 0)
            pixels.append(
                {
                    "shot": name,
                    "pixels_per_metre": float(view.pixels_per_metre(at)),
                    "joints_px": {joint: pixel(view, point) for joint, point in joints.items()},
                    "sight_px": {"eye": pixel(view, eye), "ahead": pixel(view, ahead)},
                    "seat_px": None if top is None else pixel(view, top),
                }
            )
        out.append(
            {
                "mark": item.mark,
                "request": item.to_data(),
                "at_m": [float(v) for v in at],
                "facing_deg": facing(figure.yaw),
                "off_mark_m": float((at - mark).length),
                "stature_m": float(figure.stature()),
                "arm_reach_m": float(figure.arm_reach()),
                "pose": Pose(dict(values), figure.sits).spec(),
                "joints_m": {joint: [float(v) for v in point] for joint, point in joints.items()},
                "sight_m": {"eye": [float(v) for v in eye], "ahead": [float(v) for v in ahead]},
                "seat": None
                if seat is None
                else {
                    "part": under,
                    "at_m": [float(v) for v in seat.at],
                    "facing_deg": facing(seat.facing),
                    "height_m": float(seat.height),
                    "depth_m": float(seat.depth),
                    "back_m": float(seat.back),
                },
                "reached": [
                    {"joint": r.joint, "to": r.to, "missed_m": float((joints[r.joint] - points[r.to]).length)}
                    for r in item.reach
                ],
                "clashes": [
                    {"limb": limb_of(c.first), "part": c.second, "depth_m": float(c.depth), "buried": bool(c.buried)}
                    for c in location.faults(figure)
                ],
                "tangled": tangles(figure.tangled()),
                "support": held,
                "carried": any(s["rests"] for s in held if s["way"] == "down"),
                "back_rests": all(backs) if backs else None,
                "at_limit": at_limits(values, PARAMETERS, MOVES),
                "shots": pixels,
            }
        )
    return {
        "contact": {"touch_m": contact.touch, "sink_m": contact.sink, "rest_m": contact.rest, "gap_m": float(GAP)},
        "skeleton": [joint.name for joint in JOINTS],
        "set_parts": parts,
        "points": {name: [float(v) for v in at] for name, at in sorted(request.points.items())},
        "figures": out,
    }


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
    parser.add_argument(
        "--blocking", type=Path, help="a blocking request (location_bridge.parse_request): mannequins to pose on marks"
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
