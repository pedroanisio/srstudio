"""The canonical joint table (ADR 0185): srlocations' 55 mannequin joints, read as strict versioned data."""

import copy
import hashlib
import json
import math
from importlib import resources

import pytest

from srstudio import skeleton as sk
from srstudio.errors import SrstudioError

RAW = json.loads(resources.files("srstudio").joinpath("assets/skeleton/humanoid.json").read_text())


def table():
    return copy.deepcopy(RAW)


def test_the_table_records_its_schema_and_its_source():
    assert sk.JOINT_TABLE.schema == "srstudio.skeleton-joints/1.0.0"
    assert sk.JOINT_TABLE.srlocations_commit == "4ae2278214de6e704d8dcbab8f293b6a47438483"
    assert sk.JOINT_TABLE.reference_height_m == 1.75
    assert len(sk.JOINTS) == 55
    assert sum(len(j.dofs) for j in sk.JOINTS) == 103


def test_the_digest_is_srlocations_own_over_joint_and_control_names():
    rows = [[row["name"], [dof["name"] for dof in row["dofs"]]] for row in RAW["joints"]]
    digest = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
    assert digest == RAW["srlocations_joints_digest"] == sk.JOINT_TABLE.srlocations_joints_digest
    assert digest.startswith("88629dcb422eb384")
    assert sk.joints_digest(sk.JOINTS) == digest


def test_the_joints_form_one_tree_with_parents_listed_first():
    seen: set[str] = set()
    roots = []
    for joint in sk.JOINTS:
        if joint.parent is None:
            roots.append(joint.name)
        else:
            assert joint.parent in seen, joint.name
        seen.add(joint.name)
    assert roots == ["hips"]
    assert len(seen) == len(sk.JOINTS)


def test_every_dof_is_named_and_unique_on_its_joint():
    for joint in sk.JOINTS:
        names = [dof.name for dof in joint.dofs]
        assert names and all(names) and len(names) == len(set(names)), joint.name
        for dof in joint.dofs:
            assert dof.low <= dof.high
            assert dof.kind in ("rotate", "translate")
            assert math.isclose(dof.axis.length, 1.0)
    assert len(sk.CONTROLS) == 103
    assert sk.CONTROLS[0] == "hips.right" and "neck.nod_down_up" in sk.CONTROLS


def test_sides_mirror_name_for_name():
    by_name = {j.name: j for j in sk.JOINTS}
    for joint in sk.JOINTS:
        if joint.side == 0:
            assert not joint.name.startswith(("left_", "right_")), joint.name
            continue
        mine, other = ("left_", "right_") if joint.side < 0 else ("right_", "left_")
        assert joint.name.startswith(mine)
        twin = by_name[other + joint.name[len(mine) :]]
        assert twin.side == -joint.side and twin.region == joint.region
        assert [d.name for d in twin.dofs] == [d.name for d in joint.dofs]
        assert (twin.parent is None) == (joint.parent is None)
        if joint.parent in by_name and by_name[joint.parent].side:
            assert twin.parent == other + joint.parent[len(mine) :]
        else:
            assert twin.parent == joint.parent
        assert twin.offset.mirror() == joint.offset
        for a, b in zip(joint.dofs, twin.dofs, strict=True):
            assert (a.low, a.high) == (b.low, b.high)
            # A mirror keeps a pitch (about x) and reverses a turn about y or z.
            assert math.isclose(a.axis.x, b.axis.x) and math.isclose(a.axis.y, -b.axis.y)
            assert math.isclose(a.axis.z, -b.axis.z)


def test_spot_values_match_the_mannequin_source_at_the_pin():
    # mannequin.py at 4ae2278: hip flexion 134 and knee flexion 142 (Soucie), arm down-up -135..90, eye 10/15.
    leg = sk.joint("right_upper_leg").dof("front_back")
    assert (leg.low, leg.high) == pytest.approx((math.radians(-134), math.radians(30)))
    assert sk.joint("left_lower_leg").dof("stretch").low == pytest.approx(math.radians(-142))
    arm = sk.joint("left_upper_arm").dof("down_up")
    assert (arm.low, arm.high) == pytest.approx((math.radians(-135), math.radians(90)))
    assert sk.joint("hips").dof("up").kind == "translate" and sk.joint("hips").dof("up").high == 2
    assert sk.joint("right_upper_arm").offset == sk.Vec3(0.11, -0.013, 0)  # srlocations' y up, flipped to y down
    assert sk.joint("hips").offset == sk.Vec3(0, -0.55, 0)
    assert sk.joint("right_index_distal").tip == sk.Vec3(0.011, 0, 0)
    assert sk.joint("head").tip == sk.Vec3(0, -0.102, 0)
    assert sk.joint("left_thumb_proximal").rest != sk.Quaternion()
    assert sk.joint("head").controls == ("head.nod_down_up", "head.tilt_left_right", "head.turn_left_right")
    assert sk.JOINT_TABLE.head_radius == 0.06


def test_an_unknown_joint_or_dof_is_a_typed_error():
    with pytest.raises(sk.SkeletonError) as caught:
        sk.joint("tail")
    assert isinstance(caught.value, SrstudioError) and caught.value.to_dict()["code"] == "skeleton.unknown"
    with pytest.raises(sk.SkeletonError):
        sk.joint("head").dof("wag")


def test_the_table_round_trips_through_its_parser():
    assert sk.parse_joint_table(table()) == sk.JOINT_TABLE
    assert sk.read_joint_table(json.dumps(RAW)) == sk.JOINT_TABLE


@pytest.mark.parametrize(
    "edit",
    [
        lambda t: t.update(extra=1),
        lambda t: t.pop("srlocations_commit"),
        lambda t: t.update(schema="srstudio.skeleton-joints/2.0.0"),
        lambda t: t.update(schema=7),
        lambda t: t.update(srlocations_commit="4ae2278"),
        lambda t: t.update(srlocations_joints_digest="0" * 64),
        lambda t: t.update(reference_height_m=True),
        lambda t: t.update(reference_height_m=-1),
        lambda t: t.update(head_radius=0),
        lambda t: t.update(joints=[]),
        lambda t: t.update(joints={}),
        lambda t: t["joints"].append(copy.deepcopy(t["joints"][0])),
        lambda t: t["joints"][0].update(colour="red"),
        lambda t: t["joints"][1].update(parent="nowhere"),
        lambda t: t["joints"][1].update(parent="spine"),
        lambda t: t["joints"][0].update(parent=None, name="hips2"),
        lambda t: t["joints"][1].update(parent=None),
        lambda t: t["joints"][1].update(side=2),
        lambda t: t["joints"][1].update(side=False),
        lambda t: t["joints"][1].update(region="wing"),
        lambda t: t["joints"][1].update(name="Spine!"),
        lambda t: t["joints"][1].update(offset=[0, 1]),
        lambda t: t["joints"][1].update(offset=[0, float("nan"), 0]),
        lambda t: t["joints"][1].update(offset=[0, "1", 0]),
        lambda t: t["joints"][1].update(rest=[0, 0, 0, 0]),
        lambda t: t["joints"][1].update(rest=[0.5, 0.5, 0.5, 0.6]),
        lambda t: t["joints"][1].update(tip=[1e9, 0, 0]),
        lambda t: t["joints"][1].update(dofs=[]),
        lambda t: t["joints"][1]["dofs"].append(copy.deepcopy(t["joints"][1]["dofs"][0])),
        lambda t: t["joints"][1]["dofs"][0].update(kind="slide"),
        lambda t: t["joints"][1]["dofs"][0].update(axis=[1, 1, 0]),
        lambda t: t["joints"][1]["dofs"][0].update(axis=[0.6, 0.8, 0]),
        lambda t: t["joints"][1]["dofs"][0].update(low=1, high=0),
        lambda t: t["joints"][1]["dofs"][0].update(low=-10, high=10),
        lambda t: t["joints"][1]["dofs"][0].update(name=""),
        lambda t: t["joints"][1]["dofs"][0].pop("axis"),
        lambda t: t["joints"][1]["dofs"].__setitem__(0, "pitch"),
        lambda t: t["joints"][1]["dofs"][1].update(axis=[1, 0, 0]),
        lambda t: t["joints"][0]["dofs"][0].update(low=-20, high=20),
        lambda t: t.update(digest="x"),
        lambda t: t["joints"][1]["dofs"][0].update(kind="translate", low=-1, high=1),
    ],
)
def test_a_malformed_table_is_refused(edit):
    data = table()
    edit(data)
    with pytest.raises(sk.SkeletonSchemaError):
        sk.parse_joint_table(data)


@pytest.mark.parametrize(
    "text", ["{", "[]", '{"schema": NaN}', '{"schema": 1, "schema": 2}', " " * (sk.MAX_RECORD_BYTES + 1)]
)
def test_text_that_is_not_one_strict_json_object_is_refused(text):
    with pytest.raises(sk.SkeletonSchemaError):
        sk.read_joint_table(text)


def test_a_table_is_refused_when_the_digest_disagrees_with_its_names():
    data = table()
    data["joints"][5]["dofs"][0]["name"] = "nod"
    with pytest.raises(sk.SkeletonSchemaError, match="digest"):
        sk.parse_joint_table(data)
