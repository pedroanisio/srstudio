"""The pose-track reader (ADR 0203): a pose estimator's record is untrusted until it parses strictly and its numbers
agree with each other. Every refusal is a typed error at a path."""

import json
import math

import pytest

from srstudio import pose_track as pt
from srstudio.errors import SrstudioError
from support.pose_records import edited, image, record, world


def test_a_synthetic_record_reads_back_with_its_landmarks_in_order():
    track = pt.from_data(record(40, lost=(0, 7)))
    assert track.schema_version == "1.0.0"
    assert track.fps == 30.0 and track.start_frame == 0 and len(track.frames) == 40
    assert track.found == 38 and not track.frames[7].found and track.frames[7].image is None
    assert track.subject.first_frame == 1
    knee = pt.LANDMARKS.index("left_knee")
    assert track.frames[3].world is not None and track.frames[3].world[knee] == (0.1, 0.42, -0.02)
    assert track.frames[3].image is not None and track.frames[3].image[knee][3] == 0.95
    assert len(pt.LANDMARKS) == 33 and len(set(pt.LANDMARKS)) == 33


def test_text_and_files_parse_alike(tmp_path):
    data = record(20)
    path = tmp_path / "track.json"
    path.write_text(json.dumps(data))
    assert pt.load(path) == pt.parse(json.dumps(data)) == pt.parse(json.dumps(data).encode())


@pytest.mark.parametrize(
    "text",
    ['{"schema": NaN}', '{"a": 1, "a": 2}', "[1, 2", b"\xff\xfe", '{"schema": Infinity}'],
    ids=["nan", "repeated-key", "broken", "not-utf8", "infinity"],
)
def test_malformed_text_is_refused(text):
    with pytest.raises(pt.RecordFormatError):
        pt.parse(text)


def test_an_oversized_or_unreadable_record_is_refused(tmp_path):
    with pytest.raises(pt.RecordFormatError, match="at most"):
        pt.parse(" " * (pt.MAX_BYTES + 1))
    with pytest.raises(pt.RecordFormatError, match="cannot read"):
        pt.load(tmp_path / "missing.json")


@pytest.mark.parametrize(
    ("path", "value", "error", "words"),
    [
        ("extra", 1, pt.RecordFormatError, "unknown field"),
        ("tool", ..., pt.RecordFormatError, "lacks field"),
        ("schema", "srstudio.pose-track/2.0.0", pt.SchemaVersionError, "reads"),
        ("schema", "srstudio.motion/1.0.0", pt.RecordFormatError, "schema is"),
        ("estimator.model_sha256", "short", pt.RecordFormatError, "model_sha256"),
        ("estimator.name", 7, pt.RecordFormatError, "estimator.name"),
        ("source.fps", 0.5, pt.RecordValueError, "source.fps"),
        ("source.fps", True, pt.RecordFormatError, "finite number"),
        ("source.width", 2.5, pt.RecordFormatError, "whole number"),
        ("axes.world", "metres, z toward the camera", pt.RecordFormatError, "axes"),
        ("landmarks.0", "head", pt.RecordFormatError, "BlazePose"),
        ("subject.pick", "tallest", pt.RecordFormatError, "subject.pick"),
        ("subject.point", [0.5, 0.5], pt.RecordValueError, "central pick"),
        ("subject.first_frame", 3, pt.RecordValueError, "first found"),
        ("subject.first_frame", None, pt.RecordValueError, "names the first frame"),
        ("frames", [], pt.RecordValueError, "at least one frame"),
        ("frames.2.index", 5, pt.RecordValueError, "in order"),
        ("frames.2.t_s", 0.5, pt.RecordValueError, "off the clock"),
        ("frames.2.world", None, pt.RecordValueError, "or none of them"),
        ("frames.2.world.4", [0.1, 0.2], pt.RecordFormatError, "holds 3 numbers"),
        ("frames.2.world.4.1", 40.0, pt.RecordValueError, "lies in"),
        ("frames.2.world.4.1", "0.1", pt.RecordFormatError, "finite number"),
        ("frames.2.image.3.3", 1.2, pt.RecordValueError, "visibility"),
        ("frames.2.image.3.4", -0.1, pt.RecordValueError, "presence"),
        ("frames.2.image", [[0.5, 0.5, 0.0, 1.0, 1.0]], pt.RecordFormatError, "33 landmarks"),
        ("frames.2.image", "dots", pt.RecordFormatError, "JSON list"),
        ("frames.2.box", [0.7, 0.1, 0.3, 0.9], pt.RecordValueError, "corners"),
        ("frames.2.box", [0.1, 0.2], pt.RecordFormatError, "x0, y0"),
        ("frames.2.appearance", 1.5, pt.RecordValueError, "appearance"),
        ("frames.2.position", -1, pt.RecordValueError, "position"),
        ("frames.2", "frame", pt.RecordFormatError, "JSON object"),
    ],
)
def test_a_record_that_breaks_its_schema_is_refused_at_its_path(path, value, error, words):
    with pytest.raises(error, match=words) as caught:
        pt.from_data(edited(record(10), path, value))
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)


def test_a_point_pick_needs_its_point_in_the_frame():
    data = edited(record(10), "subject.pick", "point")
    with pytest.raises(pt.RecordFormatError, match="JSON list"):
        pt.from_data(data)
    with pytest.raises(pt.RecordFormatError, match=r"\[x, y\]"):
        pt.from_data(edited(data, "subject.point", [0.5]))
    with pytest.raises(pt.RecordValueError, match="lies in"):
        pt.from_data(edited(data, "subject.point", [0.5, 1.5]))
    assert pt.from_data(edited(data, "subject.point", [0.4, 0.6])).subject.point == (0.4, 0.6)


def test_a_track_that_never_finds_the_dancer_names_no_first_frame():
    data = edited(record(6, lost=tuple(range(6))), "subject.first_frame", None)
    track = pt.from_data(data)
    assert track.found == 0 and track.subject.first_frame is None
    with pytest.raises(pt.RecordValueError, match="holds no dancer"):
        pt.from_data(edited(record(6, lost=(0,)), "subject.first_frame", 0))


def test_frames_beyond_the_source_are_refused():
    data = edited(record(10), "source.frames", 8)
    with pytest.raises(pt.RecordFormatError, match="at most 8"):
        pt.from_data(data)
    with pytest.raises(pt.RecordValueError, match="start_frame"):
        pt.from_data(edited(record(10), "start_frame", 10))


def test_an_adversarial_record_with_huge_lists_is_refused_before_it_is_read():
    data = record(3)
    data["frames"][1]["world"] = [[0.0, 0.0, 0.0]] * 10_000
    with pytest.raises(pt.RecordFormatError, match="at most 33"):
        pt.from_data(data)
    data = record(3)
    data["frames"][1]["world"][0] = [0.0] * 1000
    with pytest.raises(pt.RecordFormatError, match="at most 3"):
        pt.from_data(data)


def test_a_record_starting_mid_video_keeps_its_clock():
    data = record(10)
    for i, frame in enumerate(data["frames"]):
        frame["index"] = 100 + i
        frame["t_s"] = (100 + i) / 30
    data["start_frame"] = 100
    data["source"]["frames"] = 200
    data["subject"]["first_frame"] = 100
    track = pt.from_data(data)
    assert track.frames[0].index == 100 and math.isclose(track.frames[0].time_s, 100 / 30)


# --- provenance (ADR 0202): measured in the picture, estimated in depth, or not observed at all -------------------

AT = {name: i for i, name in enumerate(pt.LANDMARKS)}


def _posed(**moved):
    """The synthetic figure's world landmarks, some moved (metres, estimator axes), and its image landmarks."""
    rows = [list(row) for row in world(0.0)]
    for name, place in moved.items():
        rows[AT[name]] = list(place)
    frame = pt.from_data(_with(record(1), rows)).frames[0]
    assert frame.image is not None and frame.world is not None
    return frame.image, frame.world


def _with(data, rows):
    data["frames"][0]["world"] = rows
    data["frames"][0]["image"] = image(rows)
    return data


def test_a_track_with_only_image_landmarks_observes_no_twist():
    picture, _ = _posed()
    found = pt.frame_provenance(picture, None)
    assert {t.provenance for t in found.twists.values()} == {pt.UNOBSERVED}
    assert set(found.twists) == {rule.bone for rule in pt.TWIST_RULES}
    assert "depth" in found.twists["right_lower_arm"].why
    knee = found.landmarks[AT["left_knee"]]
    assert (knee.image_xy, knee.image_depth, knee.world) == (pt.MEASURED_2D, pt.ESTIMATED_3D, pt.UNOBSERVED)


def test_with_world_landmarks_a_twist_is_estimated_only_where_a_landmark_lies_across_its_bone():
    picture, rows = _posed()
    found = pt.frame_provenance(picture, rows)
    # The figure's shoulders and ears lie across the trunk and the neck: the torso's turn and the head's are read.
    assert found.twists["spine"].provenance == pt.ESTIMATED_3D
    assert found.twists["head"].provenance == pt.ESTIMATED_3D
    # Its arms and legs hang nearly straight and its hand and foot landmarks sit on the wrist and the ankle.
    for bone in ("right_upper_arm", "right_lower_arm", "right_upper_leg", "right_foot", "right_hand"):
        assert found.twists[bone].provenance == pt.UNOBSERVED, bone
    # A shin's roll and the ankle's own twist move the foot alike, and the neck's and the head's turn the face alike.
    shin = found.twists["right_lower_leg"]
    assert shin.provenance == pt.UNOBSERVED and "ankle" in shin.why
    assert found.twists["neck"].provenance == pt.UNOBSERVED
    knee = found.landmarks[AT["left_knee"]]
    assert knee.world == pt.ESTIMATED_3D and knee.visibility == 0.95


def test_bending_the_elbow_past_the_measured_threshold_makes_the_upper_arm_twist_readable():
    needed = pt.SPAN_FACTOR * pt.NOISE_M
    assert needed == pytest.approx(math.sqrt(2) * 0.035 / math.tan(math.radians(30)))
    shoulder, elbow = (-0.2, -0.5, 0.0), (-0.2, -0.22, 0.0)  # the upper arm straight down, 0.28 m

    def forearm(across):
        picture, rows = _posed(right_shoulder=shoulder, right_elbow=elbow, right_wrist=(-0.2, -0.02, -across))
        return pt.frame_provenance(picture, rows).twists["right_upper_arm"]

    short, enough = forearm(needed * 0.95), forearm(needed * 1.05)
    assert short.provenance == pt.UNOBSERVED and short.perpendicular_m == pytest.approx(needed * 0.95)
    assert enough.provenance == pt.ESTIMATED_3D and enough.needed_m == pytest.approx(needed)


def test_a_hidden_landmark_leaves_its_point_and_twist_unobserved():
    picture, rows = _posed()
    hidden = [list(row) for row in picture]
    hidden[AT["left_shoulder"]][3] = 0.1
    found = pt.frame_provenance(tuple(tuple(r) for r in hidden), rows)
    shoulder = found.landmarks[AT["left_shoulder"]]
    assert (shoulder.image_xy, shoulder.image_depth, shoulder.world) == (pt.UNOBSERVED,) * 3
    assert found.twists["spine"].provenance == pt.UNOBSERVED and "hidden" in found.twists["spine"].why


def test_a_lost_frame_observes_nothing():
    found = pt.frame_provenance(None, None)
    assert {lm.image_xy for lm in found.landmarks} == {pt.UNOBSERVED}
    assert {t.provenance for t in found.twists.values()} == {pt.UNOBSERVED}


def test_the_noise_of_a_track_is_its_landmarks_jitter():
    still = pt.from_data(record(30))
    assert pt.track_noise(still) == 0.0
    shaky = record(30)
    for i, frame in enumerate(shaky["frames"]):
        frame["world"][AT["left_wrist"]][2] += 0.01 * (-1) ** i
    assert pt.track_noise(pt.from_data(shaky)) > 0.0


@pytest.mark.parametrize(
    ("picture", "rows", "error", "words"),
    [
        ("image", None, pt.RecordFormatError, "image"),
        (((0.5, 0.5, 0.0, 1.0, 1.0),) * 3, None, pt.RecordFormatError, "33"),
        (((0.5, 0.5, 0.0, 1.0, math.nan),) * 33, None, pt.RecordFormatError, "finite"),
        (((0.5, 0.5, 0.0, 2.0, 1.0),) * 33, None, pt.RecordValueError, "lies in"),
        (None, ((0.0, 0.0, 0.0),) * 33, pt.RecordValueError, "visibility"),
        (((0.5, 0.5, 0.0, 1.0, 1.0),) * 33, ((0.0, 0.0),) * 33, pt.RecordFormatError, "3 numbers"),
    ],
)
def test_malformed_landmarks_are_refused_before_provenance(picture, rows, error, words):
    with pytest.raises(error, match=words):
        pt.frame_provenance(picture, rows)


def test_bad_settings_are_refused():
    picture, rows = _posed()
    with pytest.raises(pt.RecordValueError, match="min_visibility"):
        pt.frame_provenance(picture, rows, min_visibility=1.5)
    with pytest.raises(pt.RecordValueError, match="noise_m"):
        pt.frame_provenance(picture, rows, noise_m=0.0)


# --- 1.1.0: a repeated picture is no new observation (ADR 0204) ------------------------------------------------------


def test_a_1_1_record_says_which_frames_repeat_the_last_picture():
    track = pt.from_data(record(12, repeat=(2, 3, 7)))
    assert track.schema_version == "1.1.0" and pt.SCHEMA_VERSION == "1.1.0"
    assert track.repeats == 3 and [f.index for f in track.frames if f.repeat] == [2, 3, 7]
    assert not track.frames[2].found and track.frames[2].world is None and track.found == 9
    assert pt.from_data(record(12)).repeats == 0  # a 1.0 record: every frame its own picture


@pytest.mark.parametrize(
    ("data", "error", "words"),
    [
        (edited(record(6), "frames.2.repeat", False), pt.RecordFormatError, "unknown field"),  # not in 1.0
        (edited(record(6, repeat=()), "frames.2.repeat", ...), pt.RecordFormatError, "lacks field"),
        (edited(record(6, repeat=()), "frames.2.repeat", 1), pt.RecordFormatError, "true or false"),
        (edited(record(6, repeat=()), "frames.2.repeat", "yes"), pt.RecordFormatError, "true or false"),
        (edited(record(6, repeat=()), "frames.2.repeat", True), pt.RecordValueError, "holds no landmarks"),
        (edited(record(6, repeat=(3,)), "frames.0.repeat", True), pt.RecordValueError, "holds no landmarks"),
    ],
)
def test_a_repeat_flag_outside_its_contract_is_refused(data, error, words):
    with pytest.raises(error, match=words):
        pt.from_data(data)


def test_the_first_frame_cannot_repeat_a_picture_before_it():
    data = record(6, repeat=(0,))
    data["subject"]["first_frame"] = 1
    with pytest.raises(pt.RecordValueError, match="first frame has no picture before it"):
        pt.from_data(data)
