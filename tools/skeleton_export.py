#!/usr/bin/env python3
"""Write srlocations' joint table and its forward kinematics on seeded poses, the reference srstudio's table is held to.

Run it with srlocations' interpreter, isolated, since srstudio's cannot import srlocations:

    /home/pals/src/studio/.venv/bin/python -I tools/skeleton_export.py --repo /home/pals/src/studio \\
        --seed 185 --poses 8 --out tests/data/skeleton/srlocations-reference.json

ADR 0185 lets ``assets/skeleton/humanoid.json`` follow ``srstudio.location_bridge.SRLOCATIONS_COMMIT`` only while
srlocations' joint table and the forward kinematics that place its joints are unchanged. This tool records both at the
pin, so ``tests/test_skeleton_reference.py`` can hold srstudio's table and its forward kinematics to them.

It runs srlocations only from the pinned export ``tools/location_export.py`` makes, as ``tools/motion_export.py``
does: that tool's ``export()`` writes the pinned commit from git's object store to ``generated/srlocations/<commit>``
and checks it file by file, before and after the run, and its ``check_loaded()`` refuses an srlocations module loaded
from anywhere else. It uses ``srlocations.stock.mannequin``'s public names only: ``JOINTS``, ``JOINTS_VERSION``,
``PARAMETERS`` and ``Mannequin(...).frames()``.

The record holds, in srlocations' own units and axes (x right, y up, z away; degrees; offsets as shares of the height):
every joint's name, parent, side, offset and controls (name, turn, sign, low, high); srlocations' digest of the joint
and control names; and, for each pose, every control's value, drawn by ``random.Random(seed)`` uniformly within its
limits in ``PARAMETERS`` order and rounded to ``DECIMALS`` places, with every joint's world position in metres on the
stock man (kind ``man``, 1.75 m), not grounded, so the hips stay at their height above the origin.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import random
import sys
import tempfile
import types
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "srstudio.skeleton-reference/1.0.0"
JOINT_COUNT, CONTROL_COUNT = 55, 103  # srlocations' mannequin at the pin, as srstudio's table holds it
DECIMALS = 6  # of a degree or a metre: a drawn value is rounded, then clamped to its limits, before it is posed
MAX_POSES = 64
MAX_SEED = 2**32 - 1
KIND = "man"  # srlocations' stock man: Build() at 1.75 m, every share 1


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


def draw(parameters: Mapping[str, Any], poses: int, seed: int) -> list[dict[str, float]]:
    """``poses`` sets of every control's value, each drawn uniformly within its limits, in ``parameters``' order."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
        raise ExportError(f"--seed is a whole number from 0 to {MAX_SEED}, not {seed!r}")
    if isinstance(poses, bool) or not isinstance(poses, int) or not 1 <= poses <= MAX_POSES:
        raise ExportError(f"--poses is a whole number from 1 to {MAX_POSES}, not {poses!r}")
    rng = random.Random(seed)
    drawn = []
    for _ in range(poses):
        values = {}
        for key, dof in parameters.items():
            value = round(rng.uniform(dof.low, dof.high), DECIMALS)
            values[key] = min(max(value, float(dof.low)), float(dof.high))
        drawn.append(values)
    return drawn


def _numbers(value: Any, path: str) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ExportError(f"{path}: every number of the record is finite, not {value}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _numbers(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _numbers(item, f"{path}[{index}]")


def check(record: Mapping[str, Any]) -> None:
    """The record has the shape the reference test reads: 55 joints, 103 controls, every pose complete and finite."""
    joints = record.get("joints", [])
    names = [joint["name"] for joint in joints]
    controls = [f"{joint['name']}.{dof['name']}" for joint in joints for dof in joint["dofs"]]
    if (len(joints), len(controls)) != (JOINT_COUNT, CONTROL_COUNT):
        raise ExportError(
            f"a reference holds {JOINT_COUNT} joints and {CONTROL_COUNT} controls, not {len(joints)} and "
            f"{len(controls)}"
        )
    for index, pose in enumerate(record.get("poses", [])):
        if list(pose["values"]) != controls or set(pose["positions_m"]) != set(names):
            raise ExportError(f"poses[{index}] names every control and joint of the table, and nothing else")
    _numbers(record, "record")


def write(record: dict[str, Any], out: Path) -> Path:
    """``record`` as JSON at ``out`` (folder 700, file 600), after :func:`check` passes it."""
    check(record)
    text = json.dumps(record, indent=1, sort_keys=False, allow_nan=False) + "\n"
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
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


def _reference(commit: str, seed: int, poses: int) -> dict[str, Any]:
    """The record, from the srlocations already on ``sys.path``."""
    mannequin = importlib.import_module("srlocations.stock.mannequin")  # srstudio's interpreter has no srlocations

    version = getattr(mannequin, "JOINTS_VERSION", None)
    if not isinstance(version, str):
        raise ExportError("srlocations.stock.mannequin has no JOINTS_VERSION at the pin")
    joints = [
        {
            "name": joint.name,
            "parent": joint.parent,
            "side": joint.side,
            "offset": [float(c) for c in joint.offset],
            "dofs": [
                {"name": d.name, "turn": d.turn, "sign": d.sign, "low": float(d.low), "high": float(d.high)}
                for d in joint.dofs
            ],
        }
        for joint in mannequin.JOINTS
    ]
    names = [[joint["name"], [dof["name"] for dof in joint["dofs"]]] for joint in joints]
    recorded = []
    for values in draw(mannequin.PARAMETERS, poses, seed):
        figure = mannequin.Mannequin(pose=values, kind=KIND, grounded=False, lower=False)
        frames = figure.frames()
        positions = {
            name: [frames[name].position.x, frames[name].position.y, frames[name].position.z]
            for name in (joint["name"] for joint in joints)
        }
        recorded.append({"values": values, "positions_m": positions})
    return {
        "schema": SCHEMA,
        "srlocations_commit": commit,
        "joints_version": version,
        "joints_digest": hashlib.sha256(json.dumps(names).encode()).hexdigest(),
        "height_m": float(mannequin.KINDS[KIND].height),
        "kind": KIND,
        "seed": seed,
        "joints": joints,
        "poses": recorded,
    }


def run(args: argparse.Namespace) -> Path:
    bridge = location_export.load_bridge()
    repo = args.repo.resolve()
    commit = location_export.require_commit(repo, bridge.SRLOCATIONS_COMMIT)
    if os.environ.get("SRLOCATIONS_CATALOGS"):
        raise ExportError("SRLOCATIONS_CATALOGS is set: a reference is built from the pinned library alone; unset it")
    if importlib.metadata.entry_points(group="srlocations.plugins"):
        raise ExportError("this interpreter installs srlocations plugins: a reference is built from the stock library")
    if any(name == "srlocations" or name.startswith("srlocations.") for name in sys.modules):
        raise ExportError("srlocations was imported before the exporter chose where from")
    root = location_export.export(
        repo, commit, (args.export_root or location_export.workspace_generated() / "srlocations") / commit
    )
    sys.dont_write_bytecode = True  # an import must leave the export as the commit has it
    sys.path.insert(0, str(root))
    record = _reference(commit, args.seed, args.poses)
    location_export.check_loaded(sys.modules, root)
    location_export.verify(root, location_export.tree(repo, commit), commit)  # nothing changed the export while it ran
    return write(record, args.out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--repo", type=Path, required=True, help="an srlocations git repository holding the pin")
    parser.add_argument("--seed", type=int, required=True, help="the seed of the poses' random draw")
    parser.add_argument("--poses", type=int, required=True, help=f"how many poses to draw, 1 to {MAX_POSES}")
    parser.add_argument("--out", type=Path, required=True, help="the record to write")
    parser.add_argument(
        "--export-root", type=Path, help="where pinned exports go (the workspace's generated/srlocations)"
    )
    args = parser.parse_args(argv)
    try:
        out = run(args)
    except ExportError as error:
        print(f"skeleton_export: {error}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
