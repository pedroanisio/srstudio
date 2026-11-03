"""The srlocations motion bridge (ADR 0187): mannequin motion recorded by ``tools/motion_export.py`` in srlocations' own
interpreter, read here without srlocations. The fixtures are real runs: a figure walking two metres in two seconds, and
one standing, waving and crossing its arms, both at 30 fps. Every other record in this file is a fixture broken on
purpose, so each refusal is checked against the one way a record can be wrong.
"""

import copy
import json
import math
import re
from pathlib import Path

import pytest

from srstudio import location_bridge
from srstudio import motion_bridge as mb
from srstudio.errors import SrstudioError

DATA = Path(__file__).resolve().parent / "data" / "motion-bridge"
WALK = DATA / "walk-2m-30fps.json"
POSES = DATA / "stand-wave-crossed-30fps.json"
WALK_TEXT = WALK.read_text()
WALK_DATA = json.loads(WALK_TEXT)
POSES_DATA = json.loads(POSES.read_text())


def broken(change, data=WALK_DATA) -> dict:
    """A copy of a fixture's data with ``change`` applied to it."""
    copied = copy.deepcopy(data)
    change(copied)
    return copied


def joint_index(name: str) -> int:
    return [joint for joint, _ in mb.CANONICAL_JOINTS].index(name)


# --- the records as recorded ---------------------------------------------------------------------------------------


def test_the_fixtures_are_records_of_the_pinned_srlocations():
    for path in (WALK, POSES):
        clip = mb.load(path)
        assert clip.schema_version == mb.SCHEMA_VERSION
        assert clip.srlocations_commit == mb.SRLOCATIONS_COMMIT == location_bridge.SRLOCATIONS_COMMIT
        assert clip.source.kind == "module" and clip.source.version == "1.0.0"
        assert re.fullmatch(r"[0-9a-f]{64}", clip.source.digest)
        assert clip.fps == 30.0
        assert path.stat().st_size < 300_000


def test_the_fixtures_were_made_from_the_modules_beside_them():
    import hashlib

    for record, module in ((WALK, "walk_two_metres.py"), (POSES, "stand_wave_cross.py")):
        assert mb.load(record).source.digest == hashlib.sha256((DATA / module).read_bytes()).hexdigest()


def test_the_skeleton_is_the_canonical_fifty_five_in_mannequin_order():
    clip = mb.load(WALK)
    assert len(mb.CANONICAL_JOINTS) == 55
    assert clip.joint_names == tuple(name for name, _ in mb.CANONICAL_JOINTS)
    assert [(joint.name, joint.parent) for joint in clip.skeleton] == list(mb.CANONICAL_JOINTS)
    assert clip.joint("hips").rest_offset == (0.0, 0.0, 0.0)


def test_the_walk_covers_two_metres_in_two_seconds():
    clip = mb.load(WALK)
    assert clip.frame_count == len(clip.frames) == 61
    assert clip.duration_s == pytest.approx(2.0)
    assert clip.frame(30).time_s == pytest.approx(1.0)
    first, last = clip.frames[0].root_translation, clip.frames[-1].root_translation
    # the figure walks 2 m the way it faces, anatomical forward, which is +z in srstudio as in srlocations
    assert last[2] - first[2] == pytest.approx(2.0, abs=1e-6)
    assert last[0] - first[0] == pytest.approx(0.0, abs=1e-6)


def test_srstudio_axes_have_y_down():
    clip = mb.load(WALK)
    positions = clip.positions(0)
    head, foot = positions["head"], positions["left_foot"]
    assert head[1] < foot[1], "the head is above the feet, so its y is smaller with y down"
    spine = clip.joint("spine").rest_offset
    assert spine[1] < 0 and spine[0] == 0.0


def test_the_recorded_world_positions_are_the_forward_kinematics_of_the_rotations():
    for path in (WALK, POSES):
        clip = mb.load(path)
        for frame in clip.frames:
            assert frame.world_positions is not None
            solved = clip.positions(frame.index)
            for name, recorded in frame.world_positions.items():
                assert math.dist(recorded, solved[name]) < mb.POSITION_TOLERANCE_M, (path.name, frame.index, name)


def test_every_rotation_is_a_unit_quaternion_by_canonical_name():
    clip = mb.load(POSES)
    for frame in clip.frames:
        assert tuple(frame.rotations) == clip.joint_names
        for quaternion in frame.rotations.values():
            assert math.isclose(math.fsum(c * c for c in quaternion), 1.0, abs_tol=1e-6)


def test_the_posed_sequence_moves_the_right_arm():
    clip = mb.load(POSES)
    first, last = clip.frames[0].rotations, clip.frames[-1].rotations
    assert first["right_upper_arm"] != pytest.approx(last["right_upper_arm"], abs=1e-3)
    assert first["hips"] == pytest.approx(last["hips"], abs=1e-9)


def test_the_axes_are_converted_by_negating_y():
    """srlocations' (x, y, z) is srstudio's (x, -y, z): y flips and anatomical forward stays +z, so a rotation R
    becomes M R M with M = diag(1, -1, 1), and a quaternion (w, x, y, z) becomes (w, -x, y, -z). Checked against the
    raw record, so the reader cannot pass by converting nothing."""
    clip = mb.load(POSES)
    raw = POSES_DATA["frames"][7]
    frame = clip.frame(7)
    x, y, z = raw["root_translation_m"]
    assert frame.root_translation == (x, -y, z)
    for index, (name, _) in enumerate(mb.CANONICAL_JOINTS):
        w, a, b, c = raw["local_rotations_wxyz"][index]
        assert frame.rotations[name] == (w, -a, b, -c)
        px, py, pz = raw["world_positions_m"][index]
        assert frame.world_positions is not None and frame.world_positions[name] == (px, -py, pz)
    offset = POSES_DATA["joints"][joint_index("left_upper_arm")]["rest_offset_m"]
    assert clip.joint("left_upper_arm").rest_offset == (offset[0], -offset[1], offset[2])


def test_the_face_and_toes_point_to_anatomical_forward():
    """srstudio.body's z is the figure's anatomical forward, so the eyes and toes sit ahead of their bones on +z."""
    clip = mb.load(WALK)
    for name in ("left_eye", "right_eye", "jaw", "left_toes", "right_toes"):
        assert clip.joint(name).rest_offset[2] > 0, name


def test_the_rest_offsets_are_the_shared_skeletons():
    """The record's bones are srstudio.skeleton's joint table at the mannequin's height, axis for axis. The thumbs
    are left out: the table bakes their splay into the first joint's rest, the record into the T-stance offsets."""
    from srstudio import skeleton

    table = skeleton.JOINT_TABLE
    clip = mb.load(WALK)
    for joint in table.joints[1:]:
        if "thumb" in joint.name:
            continue
        scaled = tuple(table.reference_height_m * value for value in (joint.offset.x, joint.offset.y, joint.offset.z))
        assert clip.joint(joint.name).rest_offset == pytest.approx(scaled, abs=1e-4), joint.name


def test_text_and_data_read_the_same_clip():
    assert mb.parse(WALK_TEXT) == mb.parse(WALK_TEXT.encode()) == mb.from_data(WALK_DATA) == mb.load(WALK)


def test_a_record_without_world_positions_is_read():
    def strip(data):
        for frame in data["frames"]:
            del frame["world_positions_m"]

    clip = mb.from_data(broken(strip))
    assert all(frame.world_positions is None for frame in clip.frames)
    assert clip.positions(3) == mb.load(WALK).positions(3)


def test_a_bvh_source_reads_with_its_report():
    def bvh(data):
        data["source"] = {
            "kind": "bvh",
            "file": "take-01.bvh",
            "digest": "b" * 64,
            "unknown_bones": ["prop_sword"],
            "clamped_controls": ["right_lower_arm.stretch"],
        }

    clip = mb.from_data(broken(bvh))
    assert (clip.source.kind, clip.source.name, clip.source.version, clip.source.figure) == (
        "bvh",
        "take-01.bvh",
        None,
        None,
    )
    assert clip.source.unknown_bones == ("prop_sword",)
    assert clip.source.clamped_controls == ("right_lower_arm.stretch",)


def test_an_unknown_joint_or_frame_is_named():
    clip = mb.load(WALK)
    with pytest.raises(mb.UnknownJointError, match="tail"):
        clip.joint("tail")
    for index in (-1, 61):
        with pytest.raises(mb.FrameIndexError, match="61 frames"):
            clip.frame(index)
    with pytest.raises(mb.FrameIndexError):
        clip.positions(61)


# --- malformed, incomplete and adversarial records -----------------------------------------------------------------


def _set(path, value):
    """A change that sets the field at ``path`` (keys and list indexes)."""

    def change(data):
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return change


def _drop(path):
    def change(data):
        target = data
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return change


SHAPE = {
    "unknown top-level field": _set(["note"], "hello"),
    "unknown source field": _set(["source", "author"], "me"),
    "unknown joint field": _set(["joints", 3, "length_m"], 0.1),
    "unknown frame field": _set(["frames", 0, "time_s"], 0.0),
    "missing joints": _drop(["joints"]),
    "missing frames": _drop(["frames"]),
    "missing rotations": _drop(["frames", 2, "local_rotations_wxyz"]),
    "missing root": _drop(["frames", 2, "root_translation_m"]),
    "fps as text": _set(["fps"], "30"),
    "fps as a boolean": _set(["fps"], True),
    "frame count as a float": _set(["frame_count"], 61.0),
    "a three-number quaternion": _set(["frames", 0, "local_rotations_wxyz", 4], [1.0, 0.0, 0.0]),
    "a quaternion as an object": _set(["frames", 0, "local_rotations_wxyz", 4], {"w": 1}),
    "a quaternion part as text": _set(["frames", 0, "local_rotations_wxyz", 4], ["1", 0, 0, 0]),
    "a root as two numbers": _set(["frames", 0, "root_translation_m"], [0.0, 1.0]),
    "rotations as an object": _set(["frames", 0, "local_rotations_wxyz"], {"hips": [1, 0, 0, 0]}),
    "joints as an object": _set(["joints"], {"hips": {}}),
    "a frame as a list": _set(["frames", 0], []),
    "a parent as a number": _set(["joints", 1, "parent"], 0),
    "commit as a number": _set(["srlocations_commit"], 2742),
    "a schema of another name": _set(["schema"], "srstudio.location/1.0.0"),
    "a schema without a version": _set(["schema"], "srstudio.motion"),
    "a source kind that is neither": _set(["source", "kind"], "glb"),
    "a bvh source naming a module": _set(["source", "kind"], "bvh"),
    "a digest that is not sha256": _set(["source", "digest"], "301e57"),
    "a version that is not semver": _set(["source", "version"], "latest"),
    "a name with a control character": _set(["source", "figure"], "walker\n"),
    "an empty figure name": _set(["source", "figure"], ""),
    "axes of another convention": _set(["axes"], {"x": "right", "y": "down", "z": "forward"}),
    "axes with an extra key": _set(["axes", "w"], "time"),
    "too many frames": _set(["frames"], [{}] * (mb.MAX_FRAMES + 1)),
    "too many joints": _set(["joints"], [{}] * 56),
    "an infinite root": _set(["frames", 0, "root_translation_m"], [math.inf, 0.0, 0.0]),
    "a NaN rotation": _set(["frames", 0, "local_rotations_wxyz", 0], [math.nan, 0.0, 0.0, 0.0]),
    "an infinite world position": _set(["frames", 0, "world_positions_m", 9], [0.0, -math.inf, 0.0]),
    "an infinite fps": _set(["fps"], math.inf),
}


@pytest.mark.parametrize("change", SHAPE.values(), ids=SHAPE.keys())
def test_a_record_of_the_wrong_shape_is_refused(change):
    with pytest.raises(mb.RecordFormatError):
        mb.from_data(broken(change))


def _rotation(frame: int, joint: str, value):
    return _set(["frames", frame, "local_rotations_wxyz", joint_index(joint)], value)


def _bvh_source(**fields):
    def change(data):
        data["source"] = {
            "kind": "bvh",
            "file": "take.bvh",
            "digest": "c" * 64,
            "unknown_bones": [],
            "clamped_controls": [],
            **fields,
        }

    return change


SHAPE_BVH = {
    "a file name with a folder": _bvh_source(file="../take.bvh"),
    "a file name that is not a bvh": _bvh_source(file="take.glb"),
    "an unknown bone that is not text": _bvh_source(unknown_bones=[3]),
    "a clamped control that is not joint.control": _bvh_source(clamped_controls=["stretch"]),
    "too many unknown bones": _bvh_source(unknown_bones=[f"b{i}" for i in range(mb.MAX_REPORTED + 1)]),
}


@pytest.mark.parametrize("change", SHAPE_BVH.values(), ids=SHAPE_BVH.keys())
def test_a_bvh_source_of_the_wrong_shape_is_refused(change):
    with pytest.raises(mb.RecordFormatError):
        mb.from_data(broken(change))


def _swap_joints(data):
    data["joints"][9], data["joints"][13] = data["joints"][13], data["joints"][9]


def _rename_joint(data):
    data["joints"][6]["name"] = "left_eyeball"


def _two_roots(data):
    data["joints"][9]["parent"] = None


def _parent_after_child(data):
    data["joints"][1]["parent"] = "chest"


def _parent_unknown(data):
    data["joints"][1]["parent"] = "pelvis"


def _parent_itself(data):
    data["joints"][1]["parent"] = "spine"


def _name_twice(data):
    data["joints"][7]["name"] = "left_eye"


def _reparent(data):
    """Hangs the left eye off the jaw: still a tree, every parent before its child, but not the mannequin's."""
    data["joints"][6]["parent"] = "jaw"
    data["joints"][6], data["joints"][8] = data["joints"][8], data["joints"][6]


def _stretch_shin(data):
    """Moves the left foot 5 cm down the shin in one frame's recorded positions, and everything below it with it."""
    frame = data["frames"][12]["world_positions_m"]
    for name in ("left_foot", "left_toes"):
        frame[joint_index(name)][1] -= 0.05


def _tilt_one_rotation(data):
    """Turns the right forearm by a small, still unit, rotation the recorded positions do not show."""
    angle = 0.05
    frame = data["frames"][20]["local_rotations_wxyz"]
    w, x, y, z = frame[joint_index("right_lower_arm")]
    c, s = math.cos(angle / 2), math.sin(angle / 2)
    frame[joint_index("right_lower_arm")] = [c * w - s * z, c * x + s * y, c * y - s * x, c * z + s * w]


def _move_root(data):
    data["frames"][5]["root_translation_m"][0] += 0.01


def _positions_in_some_frames(data):
    del data["frames"][3]["world_positions_m"]


def _rotations_short(data):
    del data["frames"][0]["local_rotations_wxyz"][-1]


def _positions_short(data):
    del data["frames"][0]["world_positions_m"][-1]


def _scale_quaternion(data):
    data["frames"][0]["local_rotations_wxyz"][joint_index("neck")] = [2.0, 0.0, 0.0, 0.0]


def _root_offset(data):
    data["joints"][0]["rest_offset_m"] = [0.0, 0.1, 0.0]


def _long_bone(data):
    data["joints"][1]["rest_offset_m"] = [0.0, mb.MAX_OFFSET_M + 1.0, 0.0]


def _no_bone(data):
    data["joints"][1]["rest_offset_m"] = [0.0, 0.0, 0.0]


def _far_root(data):
    data["frames"][0]["root_translation_m"] = [mb.MAX_DISTANCE_M + 1.0, 0.0, 0.0]


SEMANTIC = {
    "two joints swapped": _swap_joints,
    "a joint renamed": _rename_joint,
    "two roots": _two_roots,
    "a parent after its child": _parent_after_child,
    "a parent that is no joint": _parent_unknown,
    "a joint its own parent": _parent_itself,
    "a joint named twice": _name_twice,
    "a tree that is not the mannequin's": _reparent,
    "a bone stretched in one frame": _stretch_shin,
    "a rotation the positions do not show": _tilt_one_rotation,
    "a root the hips are not at": _move_root,
    "world positions in some frames only": _positions_in_some_frames,
    "a rotation missing": _rotations_short,
    "a world position missing": _positions_short,
    "a quaternion that is not unit": _scale_quaternion,
    "a zero quaternion": _rotation(0, "neck", [0.0, 0.0, 0.0, 0.0]),
    "a root with an offset": _root_offset,
    "a bone longer than a body": _long_bone,
    "a bone of no length": _no_bone,
    "a root out of any set": _far_root,
    "a frame count that is not the frames": _set(["frame_count"], 60),
    "no frames": _set(["frames"], []),
    "fps of zero": _set(["fps"], 0.0),
    "fps past the bound": _set(["fps"], mb.MAX_FPS + 1.0),
    "a negative start": _set(["start_s"], -1.0),
    "a start past a day": _set(["start_s"], mb.MAX_START_S + 1.0),
    "a repeated unknown bone": _bvh_source(unknown_bones=["sword", "sword"]),
}


@pytest.mark.parametrize("change", SEMANTIC.values(), ids=SEMANTIC.keys())
def test_a_record_that_contradicts_itself_is_refused(change):
    with pytest.raises(mb.RecordValueError):
        mb.from_data(broken(change))


def test_the_broken_records_break_what_they_name():
    with pytest.raises(mb.RecordValueError, match="left_foot"):
        mb.from_data(broken(_stretch_shin))
    with pytest.raises(mb.RecordValueError, match="forward kinematics"):
        mb.from_data(broken(_tilt_one_rotation))
    with pytest.raises(mb.RecordValueError, match="canonical"):
        mb.from_data(broken(_reparent))
    with pytest.raises(mb.RecordValueError, match="unit"):
        mb.from_data(broken(_scale_quaternion))


def test_a_tilt_unchecked_by_positions_is_read():
    """Without recorded positions a unit rotation cannot be checked against anything, and is read as it is."""

    def tilt_without_positions(data):
        _tilt_one_rotation(data)
        for frame in data["frames"]:
            del frame["world_positions_m"]

    assert mb.from_data(broken(tilt_without_positions)).frame_count == 61


@pytest.mark.parametrize("version", ["2.0.0", "0.9.0"])
def test_another_schema_major_is_refused(version):
    with pytest.raises(mb.SchemaVersionError, match=version):
        mb.from_data(broken(_set(["schema"], f"srstudio.motion/{version}")))


def test_a_later_minor_of_the_same_major_is_read():
    major, minor, _ = mb.SCHEMA_VERSION.split(".")
    later = f"{major}.{int(minor) + 1}.0"
    assert mb.from_data(broken(_set(["schema"], f"srstudio.motion/{later}"))).schema_version == later


def test_a_record_of_another_srlocations_commit_is_refused():
    other = "2742fd40a1f3221c19950ebd8ba594d9c616893f"
    with pytest.raises(mb.PinError, match=other):
        mb.from_data(broken(_set(["srlocations_commit"], other)))


FPS = re.compile(r'"fps":[0-9.e+-]+')


def _fps_as(word: str) -> str:
    return FPS.sub(f'"fps":{word}', WALK_TEXT, count=1)


@pytest.mark.parametrize(
    "text",
    [
        _fps_as("NaN"),
        _fps_as("Infinity"),
        _fps_as("-Infinity"),
        _fps_as("1e999"),
        WALK_TEXT[: len(WALK_TEXT) // 2],
        "",
        "[]",
        "null",
        b"\xff\xfe not utf-8",
        WALK_TEXT.replace('{"axes":', '{"fps":1,"axes":', 1),
        " " * (mb.MAX_BYTES + 1),
    ],
    ids=["NaN", "Infinity", "-Infinity", "overflow", "truncated", "empty", "list", "null", "bytes", "duplicate", "big"],
)
def test_text_that_is_not_one_strict_json_record_is_refused(text):
    with pytest.raises(mb.RecordFormatError):
        mb.parse(text)


def test_the_broken_texts_break_what_they_name():
    assert WALK_TEXT.startswith('{"axes":'), "the fixture is written compact with sorted keys, axes first"
    assert _fps_as("NaN") != WALK_TEXT
    with pytest.raises(mb.RecordFormatError, match="finite"):
        mb.parse(_fps_as("1e999"))
    with pytest.raises(mb.RecordFormatError, match="repeats"):
        mb.parse(WALK_TEXT.replace('{"axes":', '{"fps":1,"axes":', 1))


def test_every_refusal_is_one_typed_srstudio_error():
    for error in (mb.RecordFormatError, mb.RecordValueError, mb.SchemaVersionError, mb.PinError):
        assert issubclass(error, mb.MotionRecordError)
        assert issubclass(error, ValueError)
    for error in (mb.MotionRecordError, mb.UnknownJointError, mb.FrameIndexError):
        assert issubclass(error, mb.MotionBridgeError)
    assert issubclass(mb.MotionBridgeError, SrstudioError)


def test_a_missing_file_is_a_typed_error(tmp_path):
    with pytest.raises(mb.RecordFormatError, match="nothing"):
        mb.load(tmp_path / "nothing.json")
