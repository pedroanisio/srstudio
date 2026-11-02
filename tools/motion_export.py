#!/usr/bin/env python3
"""Write a mannequin's motion from srlocations as one record srstudio reads (ADR 0187).

Run it with srlocations' interpreter, isolated, since srstudio's cannot import srlocations:

    /home/pals/src/studio/.venv/bin/python -I tools/motion_export.py --repo /home/pals/src/studio \\
        --module walk.py --figure walker --fps 30 --out RECORD.json      # a location module and a figure in it
    ... --bvh take.bvh --fps 30 --start 1 --end 3 --out RECORD.json      # a BVH take, on the stock mannequin

It runs srlocations only from the pinned export ``tools/location_export.py`` makes: that tool's ``export()`` writes the
commit ``srstudio.location_bridge.SRLOCATIONS_COMMIT`` names from git's object store to
``generated/srlocations/<commit>`` and checks it file by file, before and after the run, and its ``check_loaded()``
refuses an srlocations module loaded from anywhere else. One pin, one export folder, for both bridges.

It uses srlocations' public interface only. ``interchange.save_bvh`` writes the 55 joints' T-stance offsets and, per
frame, the hips' place and every joint's turns from the T-stance; this tool parses that BVH, which must have exactly the
layout ``save_bvh`` writes at the pin, and turns each joint's Euler turns into a unit quaternion, out of the file's
frame (z towards the viewer) into srlocations' (z away). ``Mannequin.frames()`` and ``Node.transform``, per frame,
give every joint's world position, which the record carries so srstudio can check the rotations against srlocations'
own placing of the joints. A BVH take is read by ``interchange.load_bvh`` onto the stock mannequin, and each of its
poses is written again through ``save_bvh``, so a take and a location give the same skeleton. The record is read back
through ``srstudio.motion_bridge``, loaded by path, before it is written, so the exporter writes nothing srstudio would
refuse.
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
import sys
import tempfile
import types
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
UNITS = 100.0  # save_bvh's default: centimetres to a metre
FLIP = (1.0, 1.0, -1.0)  # a BVH file's frame to srlocations' and back: z changes sign (srlocations.interchange.FLIP)
ROOT_CHANNELS = ("Xposition", "Yposition", "Zposition", "Zrotation", "Xrotation", "Yrotation")
BONE_CHANNELS = ("Zrotation", "Xrotation", "Yrotation")
QUATERNION_DECIMALS = 8
POSITION_DECIMALS = 6  # a micrometre
OFFSET_DECIMALS = 10  # save_bvh writes six decimals of a centimetre
NUMBER = re.compile(r"-?(0|[1-9]\d*)(\.\d+)?([eE][-+]?\d+)?")


def _location_export() -> types.ModuleType:
    """``tools/location_export.py``, whose export, checks and errors this tool shares."""
    if "location_export" in sys.modules:
        return sys.modules["location_export"]
    found = importlib.util.spec_from_file_location("location_export", REPO / "tools" / "location_export.py")
    if found is None or found.loader is None:
        raise RuntimeError(f"cannot load {REPO / 'tools' / 'location_export.py'}")
    module = importlib.util.module_from_spec(found)
    sys.modules[found.name] = module
    found.loader.exec_module(module)
    return module


location_export = _location_export()
ExportError = location_export.ExportError


# --- the BVH save_bvh writes ---------------------------------------------------------------------------------------


class Bone:
    def __init__(self, name: str, parent: str | None, offset: tuple[float, float, float], channels: tuple[str, ...]):
        self.name, self.parent, self.offset, self.channels = name, parent, offset, channels


def parse_bvh(text: str, fps: float) -> tuple[list[Bone], list[list[float]]]:
    """The bones and the frames of a BVH in ``save_bvh``'s layout at the pin: a root with three positions and turns
    about z, x and y, every other joint with those three turns, and frames ``1 / fps`` apart. Anything else is
    refused."""
    words = text.split()
    at = 0

    def word() -> str:
        nonlocal at
        if at >= len(words):
            raise ExportError("save_bvh's file ends in the middle")
        at += 1
        return words[at - 1]

    def number() -> float:
        found = word()
        if not NUMBER.fullmatch(found) or not math.isfinite(float(found)):
            raise ExportError(f"save_bvh's file has {found!r} where a finite number belongs")
        return float(found)

    def expect(token: str) -> None:
        found = word()
        if found != token:
            raise ExportError(f"save_bvh's file has {found!r} where {token!r} belongs")

    bones: list[Bone] = []

    def joint(parent: str | None) -> None:
        name = word()
        expect("{")
        expect("OFFSET")
        offset = (number(), number(), number())
        expect("CHANNELS")
        count = word()
        channels = tuple(word() for _ in range(int(count) if count.isdigit() else -1))
        wanted = ROOT_CHANNELS if parent is None else BONE_CHANNELS
        if channels != wanted:
            raise ExportError(f"save_bvh gave {name} the channels {channels}; at the pin it writes {wanted}")
        bones.append(Bone(name, parent, offset, channels))
        while True:
            token = word()
            if token == "JOINT":
                joint(name)
            elif token == "End":
                for part in ("Site", "{", "OFFSET"):
                    expect(part)
                for _ in range(3):
                    number()
                expect("}")
            elif token == "}":
                return
            else:
                raise ExportError(f"save_bvh's file has {token!r} inside joint {name}")

    expect("HIERARCHY")
    expect("ROOT")
    joint(None)
    expect("MOTION")
    expect("Frames:")
    count = word()
    if not count.isdigit() or int(count) < 1:
        raise ExportError(f"save_bvh's file has {count!r} frames")
    expect("Frame")
    expect("Time:")
    frame_time = number()
    if not math.isclose(frame_time, round(1 / fps, 7), abs_tol=1e-9):
        raise ExportError(f"save_bvh's frames are {frame_time} s apart, not 1/{fps} s")
    width = sum(len(bone.channels) for bone in bones)
    rows = [[number() for _ in range(width)] for _ in range(int(count))]
    if at != len(words):
        raise ExportError(f"save_bvh's file has {len(words) - at} words past its {count} frames")
    return bones, rows


def _axis(name: str, degrees: float) -> list[list[float]]:
    """A right-handed turn about a BVH file's axis (srlocations.interchange._axis)."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return {
        "X": [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]],
        "Y": [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]],
        "Z": [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]],
    }[name]


def _times(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[math.fsum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]


def turn(channels: Sequence[str], degrees: Sequence[float]) -> list[list[float]]:
    """A joint's turn in srlocations' frame from its BVH channels: each turn in the order listed, then out of the file's
    frame, where z is reversed."""
    basis = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    for channel, value in zip(channels, degrees, strict=True):
        basis = _times(basis, _axis(channel[0], value))
    return [[basis[r][c] * FLIP[r] * FLIP[c] for c in range(3)] for r in range(3)]


def quaternion(m: Sequence[Sequence[float]]) -> list[float]:
    """The unit quaternion (w, x, y, z) of a rotation matrix, w not negative, rounded for the record."""
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s = 2.0 * math.sqrt(1.0 + trace)
        q = [s / 4, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s]
    elif m[0][0] >= m[1][1] and m[0][0] >= m[2][2]:
        s = 2.0 * math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2])
        q = [(m[2][1] - m[1][2]) / s, s / 4, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s]
    elif m[1][1] >= m[2][2]:
        s = 2.0 * math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2])
        q = [(m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, s / 4, (m[1][2] + m[2][1]) / s]
    else:
        s = 2.0 * math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1])
        q = [(m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, s / 4]
    length = math.sqrt(math.fsum(c * c for c in q))
    sign = -1.0 if q[0] < 0 else 1.0
    return [_rounded(sign * c / length, QUATERNION_DECIMALS) for c in q]


def _rounded(value: float, decimals: int) -> float:
    return round(value, decimals) + 0.0  # + 0.0: never a negative zero in the record


def _point(values: Sequence[float], decimals: int, units: float = 1.0) -> list[float]:
    """A point or offset out of a BVH file's frame and units into srlocations' metres."""
    return [_rounded(v / units * f, decimals) for v, f in zip(values, FLIP, strict=True)]


def skeleton(bones: Sequence[Bone], order: Sequence[str]) -> list[dict[str, Any]]:
    """The joints in ``order`` (the mannequin's), each with its parent and its T-stance offset in metres."""
    by_name = {bone.name: bone for bone in bones}
    if sorted(by_name) != sorted(order) or len(bones) != len(order):
        raise ExportError(f"save_bvh wrote the joints {[b.name for b in bones]}; the mannequin has {list(order)}")
    return [
        {
            "name": name,
            "parent": by_name[name].parent,
            "rest_offset_m": _point(by_name[name].offset, OFFSET_DECIMALS, UNITS),
        }
        for name in order
    ]


def frame_record(bones: Sequence[Bone], row: Sequence[float], order: Sequence[str]) -> dict[str, Any]:
    """One frame of save_bvh's motion: the root's place in metres and every joint's rotation, in ``order``."""
    rotations: dict[str, list[float]] = {}
    at = 3
    for bone in bones:
        rotations[bone.name] = quaternion(turn(BONE_CHANNELS, row[at : at + 3]))
        at += 3
    return {
        "root_translation_m": _point(row[:3], OFFSET_DECIMALS, UNITS),
        "local_rotations_wxyz": [rotations[name] for name in order],
    }


def world_positions(figure: Any, order: Sequence[str]) -> list[list[float]]:
    """Every joint's place in the location, as srlocations puts it: the figure's transform on each of its frames."""
    frames = figure.frames()
    places = (figure.transform.then(frames[name]).position for name in order)
    return [[_rounded(v, POSITION_DECIMALS) for v in place] for place in places]  # already in srlocations' frame


# --- what to record ------------------------------------------------------------------------------------------------


def _times_of(start: float, end: float, fps: float) -> list[float]:
    """srlocations' frame times from ``start`` to ``end`` (srlocations.interchange's clip sampling)."""
    return [start + frame / fps for frame in range(math.floor((end - start) * fps + 1e-9) + 1)]


def _bounded(start: float, end: float, fps: float, bridge: types.ModuleType) -> None:
    """Refused before srlocations samples a single frame: a record holds at most ``MAX_FRAMES``, whatever a module's
    duration or ``--end`` says."""
    if (end - start) * fps >= bridge.MAX_FRAMES:
        raise ExportError(f"{start} to {end} s at {fps} fps is past the {bridge.MAX_FRAMES} frames a record holds")


def _module(path: Path, bridge: types.ModuleType) -> tuple[Any, dict[str, Any]]:
    from srlocations.location import Location

    found = importlib.util.spec_from_file_location(f"srlocations_motion_{path.stem}", path)
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
    return location, {"kind": "module", "name": name, "version": version, "digest": digest}


def _from_module(args: argparse.Namespace, bridge: types.ModuleType, scratch: Path) -> dict[str, Any]:
    from srlocations.interchange import save_bvh
    from srlocations.registry import CatalogError
    from srlocations.stock.mannequin import Mannequin

    location, source = _module(args.module.resolve(), bridge)
    try:
        figure = location.figure(args.figure)
    except CatalogError as error:
        raise ExportError(f"{source['name']}: {error}") from None
    if not isinstance(figure, Mannequin):
        raise ExportError(f"{args.figure} is a {type(figure).__name__}; only a mannequin has the 55 joints")
    index = next(place for place, node in enumerate(location.nodes) if node is figure)
    end = location.duration() if args.end is None else args.end
    if not 0 <= args.start <= end:
        raise ExportError(f"a clip runs forward from 0: --start {args.start} and --end {end} do not")
    _bounded(args.start, end, args.fps, bridge)
    bones, rows = parse_bvh(
        save_bvh(scratch / "motion.bvh", args.figure, location, fps=args.fps, start=args.start, end=end).read_text(),
        args.fps,
    )
    times = _times_of(args.start, end, args.fps)
    if len(times) != len(rows):
        raise ExportError(
            f"save_bvh wrote {len(rows)} frames; {args.start} to {end} s at {args.fps} fps is {len(times)}"
        )
    order = bridge.JOINT_NAMES
    frames = []
    for time, row in zip(times, rows, strict=True):
        frame = frame_record(bones, row, order)
        frame["world_positions_m"] = world_positions(location.at(time).nodes[index], order)
        frames.append(frame)
    return {
        "source": {**source, "figure": args.figure},
        "start_s": float(args.start),
        "joints": skeleton(bones, order),
        "frames": frames,
    }


def _from_bvh(args: argparse.Namespace, bridge: types.ModuleType, scratch: Path) -> dict[str, Any]:
    from srlocations.interchange import load_bvh, save_bvh
    from srlocations.stock.mannequin import Mannequin

    path = args.bvh.resolve()
    if not bridge.BVH_FILE.fullmatch(path.name):
        raise ExportError(f"a take is a .bvh file of a plain name, not {path.name!r}")
    if path.is_file() and path.stat().st_size > bridge.MAX_BYTES:
        raise ExportError(f"{path.name} is past the {bridge.MAX_BYTES} bytes a take may be")
    try:
        take = load_bvh(path)
    except (ValueError, OverflowError, IndexError, OSError) as error:  # srlocations' errors are ValueErrors
        raise ExportError(f"srlocations cannot read {path}: {error}") from None
    if not math.isclose(take.fps, args.fps, rel_tol=1e-9):
        raise ExportError(f"{path.name} runs at {take.fps} fps, not {args.fps}: a take is recorded at its own rate")
    end = (len(take.poses) - 1) / take.fps if args.end is None else args.end
    chosen = [n for n in range(len(take.poses)) if args.start - 1e-9 <= n / take.fps <= end + 1e-9]
    if not chosen:
        raise ExportError(f"{path.name} has no frame from {args.start} to {end} s")
    _bounded(chosen[0] / take.fps, chosen[-1] / take.fps, take.fps, bridge)
    order = bridge.JOINT_NAMES
    bones: list[Bone] = []
    frames = []
    for n in chosen:
        figure = Mannequin(pose=take.poses[n])
        found, rows = parse_bvh(save_bvh(scratch / f"pose-{n}.bvh", figure, fps=args.fps).read_text(), args.fps)
        if bones and [(b.name, b.parent, b.offset) for b in found] != [(b.name, b.parent, b.offset) for b in bones]:
            raise ExportError(f"save_bvh wrote another skeleton for frame {n} of {path.name}")
        bones = found
        frame = frame_record(found, rows[0], order)
        frame["world_positions_m"] = world_positions(figure, order)
        frames.append(frame)
    source = {
        "kind": "bvh",
        "file": path.name,
        "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
        "unknown_bones": list(take.unknown),
        "clamped_controls": sorted(take.clamped),
    }
    return {"source": source, "start_s": chosen[0] / take.fps, "joints": skeleton(bones, order), "frames": frames}


# --- running -------------------------------------------------------------------------------------------------------


def write(record: dict[str, Any], out: Path, bridge: types.ModuleType) -> Path:
    """``record`` as compact JSON at ``out`` (folder 700, file 600), after ``bridge.from_data`` reads it."""
    bridge.from_data(json.loads(json.dumps(record, allow_nan=False)))
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = json.dumps(record, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n"
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


def load_bridge() -> types.ModuleType:
    """srstudio's reader, from this repository, through ``location_export.load_srstudio``: in srlocations' interpreter
    only the reader and the two stdlib-only modules it imports load; srstudio's ``__init__`` never runs."""
    return location_export.load_srstudio("motion_bridge")


def run(args: argparse.Namespace, bridge: types.ModuleType) -> Path:
    if args.module is not None and not args.figure:
        raise ExportError("--module records one figure of the location: name it with --figure")
    if args.bvh is not None and args.figure:
        raise ExportError("--bvh records the take on the stock mannequin, which has no --figure to name")
    if not 0 < args.fps <= bridge.MAX_FPS or not math.isfinite(args.start) or args.start < 0:
        raise ExportError(f"--fps is above 0 and at most {bridge.MAX_FPS}, and --start a time from 0")
    if args.end is not None and not (math.isfinite(args.end) and args.start <= args.end):
        raise ExportError(f"--end is a time from --start {args.start}, not {args.end}")
    repo = args.repo.resolve()
    commit = location_export.require_commit(repo, bridge.SRLOCATIONS_COMMIT)
    if os.environ.get("SRLOCATIONS_CATALOGS"):
        raise ExportError("SRLOCATIONS_CATALOGS is set: a record is built from the pinned catalog alone; unset it")
    if importlib.metadata.entry_points(group="srlocations.plugins"):
        raise ExportError("this interpreter installs srlocations plugins: a record is built from the stock library")
    if any(name == "srlocations" or name.startswith("srlocations.") for name in sys.modules):
        raise ExportError("srlocations was imported before the exporter chose where from")
    root = location_export.export(
        repo, commit, (args.export_root or location_export.workspace_generated() / "srlocations") / commit
    )
    sys.dont_write_bytecode = True  # an import must leave the export as the commit has it
    sys.path.insert(0, str(root))
    args.out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".motion-export.", dir=args.out.parent) as scratch:
        made = (_from_module if args.module is not None else _from_bvh)(args, bridge, Path(scratch))
    location_export.check_loaded(sys.modules, root)
    location_export.verify(root, location_export.tree(repo, commit), commit)  # nothing changed the export while it ran
    record = {
        "schema": f"{bridge.SCHEMA}/{bridge.SCHEMA_VERSION}",
        "srlocations_commit": commit,
        "source": made["source"],
        "axes": dict(bridge.RECORDED_AXES),
        "fps": float(args.fps),
        "start_s": made["start_s"],
        "frame_count": len(made["frames"]),
        "joints": made["joints"],
        "frames": made["frames"],
    }
    return write(record, args.out, bridge)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--repo", type=Path, required=True, help="an srlocations git repository holding the pin")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--module", type=Path, help="a location module: NAME, VERSION and location() -> Location")
    which.add_argument("--bvh", type=Path, help="a BVH take, read onto the stock mannequin by srlocations' load_bvh")
    parser.add_argument("--figure", help="the mannequin of the location module to record, by its name")
    parser.add_argument("--fps", type=float, required=True, help="frames a second; a take's must be its own")
    parser.add_argument("--start", type=float, default=0.0, help="the first frame's time, in seconds (0)")
    parser.add_argument("--end", type=float, help="the last frame's time, in seconds (the end of the motion)")
    parser.add_argument("--out", type=Path, required=True, help="the record to write")
    parser.add_argument(
        "--export-root", type=Path, help="where pinned exports go (the workspace's generated/srlocations)"
    )
    args = parser.parse_args(argv)
    bridge = load_bridge()
    try:
        out = run(args, bridge)
    except (ExportError, bridge.MotionBridgeError) as error:
        print(f"motion_export: {error}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
