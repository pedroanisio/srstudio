"""srstudio's joint table against srlocations' own at the pin (ADR 0185): the table and its forward kinematics.

``humanoid.json`` follows ``location_bridge.SRLOCATIONS_COMMIT`` only while srlocations' joint table is unchanged. These
tests hold that invariant in srstudio. ``tests/data/skeleton/srlocations-reference.json`` is written by
``tools/skeleton_export.py`` in srlocations' interpreter from the pinned export: srlocations' joints as it defines them
(names, parents, offsets, controls with their turns, signs and limits) and the world place of every joint on a few
seeded poses within the limits, from srlocations' own forward kinematics. srstudio's table must convert to the first
and its forward kinematics must reproduce the second. With srlocations' interpreter and the pinned commit at hand, the
record is made again and compared byte for byte; without them that test skips and says why.
"""

import copy
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from importlib import resources
from pathlib import Path

import pytest

from srstudio import location_bridge as lb
from srstudio import motion_bridge as mb
from srstudio import skeleton as sk

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "skeleton_export.py"
spec = importlib.util.spec_from_file_location("skeleton_export", TOOL)
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules["skeleton_export"] = tool
spec.loader.exec_module(tool)

REFERENCE = ROOT / "tests" / "data" / "skeleton" / "srlocations-reference.json"
STUDIO = Path(os.environ.get("SRLOCATIONS_REPO", "/home/pals/src/studio"))
STUDIO_PYTHON = Path(os.environ.get("SRLOCATIONS_PYTHON", str(STUDIO / ".venv" / "bin" / "python")))
TABLE = json.loads(resources.files("srstudio").joinpath("assets/skeleton/humanoid.json").read_text())
REF = json.loads(REFERENCE.read_text())
DIGEST = "88629dcb422eb384692b6c893174a25066573d322d4f81b54c46a24538bf438d"
SEED, POSES = 185, 8
TOLERANCE = 1e-9  # metres or radians: the table is stored to twelve digits
TURNS = {"yaw": (0.0, 1.0, 0.0), "pitch": (1.0, 0.0, 0.0), "roll": (0.0, 0.0, -1.0)}  # in srstudio's axes, y down
MOVES = {"right": (1.0, 0.0, 0.0), "up": (0.0, -1.0, 0.0), "forward": (0.0, 0.0, 1.0)}
PROFILE = sk.preset("realistic")  # the canonical table at 1.75 m, srlocations' stock man


def srlocations_digest(rows: list) -> str:
    """srlocations' digest of its joint table (tests/test_mannequin.py at the pin): SHA-256 of
    ``json.dumps([[joint, [control, ...]], ...])`` with the default separators, over the joints in order."""
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def rows(joints: list) -> list:
    return [[joint["name"], [dof["name"] for dof in joint["dofs"]]] for joint in joints]


def close(a, b) -> bool:
    return len(a) == len(b) and all(abs(x - y) <= TOLERANCE for x, y in zip(a, b, strict=True))


def converted(theirs: dict, dof: dict) -> tuple[str, list[float], float]:
    """What srstudio's table holds for one of srlocations' controls: its kind, its axis, and the scale of its limits.
    A move is in metres along its way; a turn is in radians about the axis of its kind, times its sign, with a left
    joint's yaw and roll negated (srlocations' Joint.turned)."""
    if dof["turn"] in MOVES:
        return "translate", [c * dof["sign"] for c in MOVES[dof["turn"]]], 1.0
    flip = -1 if theirs["side"] < 0 and dof["turn"] in ("yaw", "roll") else 1
    return "rotate", [c * dof["sign"] * flip for c in TURNS[dof["turn"]]], math.pi / 180


def differences(table: dict, reference: dict) -> list[str]:
    """Where srstudio's table is not srlocations' at the pin, by field."""
    found = []
    if [j["name"] for j in table["joints"]] != [j["name"] for j in reference["joints"]]:
        found.append("joints")
    ours = {joint["name"]: joint for joint in table["joints"]}
    for theirs in reference["joints"]:
        name, mine = theirs["name"], ours.get(theirs["name"])
        if mine is None:
            continue
        if mine["parent"] != theirs["parent"]:
            found.append(f"{name}.parent")
        if mine["side"] != theirs["side"]:
            found.append(f"{name}.side")
        x, y, z = theirs["offset"]
        if not close(mine["offset"], [x, -y, z]):
            found.append(f"{name}.offset")
        if [d["name"] for d in mine["dofs"]] != [d["name"] for d in theirs["dofs"]]:
            found.append(f"{name}.dofs")
            continue
        for held, dof in zip(mine["dofs"], theirs["dofs"], strict=True):
            kind, axis, scale = converted(theirs, dof)
            if held["kind"] != kind:
                found.append(f"{name}.{dof['name']}.kind")
            if not close(held["axis"], axis):
                found.append(f"{name}.{dof['name']}.axis")
            if not close([held["low"], held["high"]], [dof["low"] * scale, dof["high"] * scale]):
                found.append(f"{name}.{dof['name']}.limits")
    return found


# --- the record ----------------------------------------------------------------------------------------------------


def test_the_reference_is_of_the_pinned_srlocations():
    assert REF["schema"] == tool.SCHEMA == "srstudio.skeleton-reference/1.0.0"
    assert REF["srlocations_commit"] == lb.SRLOCATIONS_COMMIT == TABLE["srlocations_commit"]
    assert REF["joints_version"] == "1.0.0"
    assert (REF["seed"], len(REF["poses"]), REF["height_m"]) == (SEED, POSES, TABLE["reference_height_m"])
    assert (len(REF["joints"]), sum(len(j["dofs"]) for j in REF["joints"])) == (55, 103)


# --- the digest ----------------------------------------------------------------------------------------------------


def test_the_digest_is_recomputed_from_the_tables_srstudio_holds():
    by_name = {joint["name"]: joint for joint in TABLE["joints"]}
    assert [(j["name"], j["parent"]) for j in TABLE["joints"]] == list(mb.CANONICAL_JOINTS)
    held = [[name, [dof["name"] for dof in by_name[name]["dofs"]]] for name in mb.JOINT_NAMES]
    assert srlocations_digest(rows(TABLE["joints"])) == srlocations_digest(held) == DIGEST
    assert (
        DIGEST == TABLE["srlocations_joints_digest"] == REF["joints_digest"] == srlocations_digest(rows(REF["joints"]))
    )


def test_a_renamed_or_moved_control_changes_the_digest():
    renamed, moved = copy.deepcopy(TABLE), copy.deepcopy(TABLE)
    renamed["joints"][20]["dofs"][0]["name"] = "bent"
    moved["joints"][3]["dofs"].reverse()
    assert srlocations_digest(rows(renamed["joints"])) != DIGEST
    assert srlocations_digest(rows(moved["joints"])) != DIGEST


def test_a_joint_srstudio_holds_under_another_parent_than_motion_bridge_is_found():
    table = copy.deepcopy(TABLE)
    table["joints"][10]["parent"] = "hips"
    assert [(j["name"], j["parent"]) for j in table["joints"]] != list(mb.CANONICAL_JOINTS)


# --- the table -----------------------------------------------------------------------------------------------------


def test_the_table_is_srlocations_table_at_the_pin():
    assert differences(TABLE, REF) == []


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda t: t["joints"][10]["offset"].__setitem__(1, t["joints"][10]["offset"][1] + 0.001), "offset"),
        (lambda t: t["joints"][10].__setitem__("parent", "hips"), "parent"),
        (lambda t: t["joints"][18]["dofs"][1].__setitem__("high", t["joints"][18]["dofs"][1]["high"] - 0.01), "limits"),
        (lambda t: t["joints"][18]["dofs"][1].__setitem__("low", t["joints"][18]["dofs"][1]["low"] + 0.01), "limits"),
        (lambda t: t["joints"][0]["dofs"][1].__setitem__("high", 2.5), "limits"),
        (lambda t: t["joints"][22]["dofs"][0].__setitem__("axis", [0.0, 0.0, 1.0]), "axis"),
    ],
    ids=["offset", "parent", "high", "low", "root-move", "axis"],
)
def test_a_changed_offset_parent_limit_or_axis_is_found(change, field):
    table = copy.deepcopy(TABLE)
    change(table)
    found = differences(table, REF)
    assert len(found) == 1 and found[0].endswith(f".{field}"), found


# --- forward kinematics --------------------------------------------------------------------------------------------


def values_of(recorded: dict) -> dict[str, float]:
    """srlocations' control values as srstudio's pose takes them: radians for a turn, metres for a move."""
    kinds = {f"{j['name']}.{d['name']}": d["turn"] in MOVES for j in REF["joints"] for d in j["dofs"]}
    return {key: value if kinds[key] else math.radians(value) for key, value in recorded.items()}


@pytest.mark.parametrize("index", range(POSES))
def test_forward_kinematics_places_every_joint_where_srlocations_does(index):
    recorded = REF["poses"][index]
    assert len(recorded["values"]) == 103
    pose = sk.pose(PROFILE, values_of(recorded["values"]), root=PROFILE.standing_root())
    frames = sk.world(PROFILE, pose)
    assert set(frames) == set(recorded["positions_m"]) == set(mb.JOINT_NAMES)
    worst = max(
        math.dist((frame.origin.x, -frame.origin.y, frame.origin.z), recorded["positions_m"][name])
        for name, frame in frames.items()
    )
    assert worst < TOLERANCE


def test_the_seeded_poses_spread_across_the_limits():
    """Each control is drawn on its own, so the poses are not the T-stance: every control moves in some pose."""
    for key in REF["poses"][0]["values"]:
        assert any(abs(pose["values"][key]) > 1e-3 for pose in REF["poses"]), key


# --- the tool, without srlocations ---------------------------------------------------------------------------------


class _Dof:
    def __init__(self, name, turn, low, high, sign=1):
        self.name, self.turn, self.low, self.high, self.sign = name, turn, low, high, sign


def test_drawn_values_are_seeded_rounded_and_within_the_limits():
    parameters = {"a.b": _Dof("b", "pitch", -10.0, 30.0), "a.c": _Dof("c", "up", -2.0, 2.0)}
    first, again = tool.draw(parameters, 3, 7), tool.draw(parameters, 3, 7)
    assert first == again and first != tool.draw(parameters, 3, 8)
    assert len(first) == 3
    for values in first:
        assert list(values) == ["a.b", "a.c"]
        for key, value in values.items():
            assert parameters[key].low <= value <= parameters[key].high
            assert round(value, tool.DECIMALS) == value


@pytest.mark.parametrize(("seed", "poses"), [(-1, 8), (185, 0), (185, tool.MAX_POSES + 1), (True, 8)])
def test_a_seed_or_count_out_of_range_is_refused(seed, poses):
    with pytest.raises(tool.ExportError):
        tool.draw({"a.b": _Dof("b", "pitch", -1.0, 1.0)}, poses, seed)


def test_a_record_of_another_shape_is_refused(tmp_path):
    record = copy.deepcopy(REF)
    record["joints"] = record["joints"][:-1]
    with pytest.raises(tool.ExportError, match="55 joints"):
        tool.write(record, tmp_path / "reference.json")
    record = copy.deepcopy(REF)
    record["poses"][0]["positions_m"]["hips"] = [math.nan, 0.0, 0.0]
    with pytest.raises(tool.ExportError, match="finite"):
        tool.write(record, tmp_path / "reference.json")
    assert not (tmp_path / "reference.json").exists()


# --- the tool, in srlocations' interpreter -------------------------------------------------------------------------


def test_the_reference_is_what_the_tool_makes_at_the_pin(tmp_path):
    if not STUDIO_PYTHON.is_file():
        pytest.skip(f"srlocations' interpreter is not at {STUDIO_PYTHON} (set SRLOCATIONS_PYTHON)")
    held = subprocess.run(
        ["git", "-C", str(STUDIO), "cat-file", "-e", f"{lb.SRLOCATIONS_COMMIT}^{{commit}}"], capture_output=True
    )
    if held.returncode:
        pytest.skip(f"{STUDIO} does not hold the pinned srlocations commit {lb.SRLOCATIONS_COMMIT} (SRLOCATIONS_REPO)")
    out = tmp_path / "reference.json"
    command = [str(STUDIO_PYTHON), "-I", str(TOOL), "--repo", str(STUDIO), "--seed", str(SEED), "--poses", str(POSES)]
    done = subprocess.run(
        [*command, "--out", str(out), "--export-root", str(tmp_path / "exports")],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert done.returncode == 0, done.stderr
    assert out.read_bytes() == REFERENCE.read_bytes()
