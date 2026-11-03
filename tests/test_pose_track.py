"""The pose-track reader (ADR 0203): a pose estimator's record is untrusted until it parses strictly and its numbers
agree with each other. Every refusal is a typed error at a path."""

import json
import math

import pytest

from srstudio import pose_track as pt
from srstudio.errors import SrstudioError
from support.pose_records import edited, record


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
