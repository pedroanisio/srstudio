"""The cleaned 2D track reader (``pose_clean``): a synthetic record reads, and every malformed, inconsistent or hostile
variant is refused with a typed error. No record here comes from a real take."""

import copy
import json

import pytest

from srstudio import pose_clean
from srstudio.pose_clean import JOINTS, RecordFormatError, RecordValueError

FPS = 30.0


def points(dx: float = 0.0) -> list[list[float]]:
    return [[100.0 + 10 * j + dx, 200.0 + 20 * j] for j in range(len(JOINTS))]


def record(count: int = 4) -> dict:
    return {
        "format": pose_clean.FORMAT,
        "fps": FPS,
        "width": 720,
        "height": 1280,
        "source": "synthetic.mp4",
        "source_frame_start": 30,
        "source_frame_end": 30 + count,
        "source_time_s": [1.0, round((30 + count) / FPS, 2)],
        "continuous_take": True,
        "duration_s": count / FPS,
        "joint_names": list(JOINTS),
        "bones": [list(b) for b in pose_clean.BONES],
        "cleaning": ["smoothed"],
        "frames": [
            {"frame": i, "time": i / FPS, "xy": points(i), "xy_stabilised": points(0.5 * i)} for i in range(count)
        ],
    }


def test_a_synthetic_record_reads_into_a_clean_track():
    track = pose_clean.from_data(record())
    assert track.fps == FPS and len(track.frames) == 4 and track.joint_names == JOINTS
    assert track.frames[2].xy[0] == (102.0, 200.0)
    assert track.points()[2][0] == (101.0, 200.0)
    assert track.points(stabilised=False)[2][0] == (102.0, 200.0)
    assert track.duration_s == pytest.approx(4 / FPS)


def test_parse_reads_the_same_record_from_its_json_text_and_bytes():
    text = json.dumps(record())
    assert pose_clean.parse(text) == pose_clean.parse(text.encode()) == pose_clean.from_data(record())


def mutate(path: str, value: object) -> dict:
    data = copy.deepcopy(record())
    *head, last = path.split(".")
    node = data
    for key in head:
        node = node[int(key)] if isinstance(node, list) else node[key]
    if value is DELETE:
        del node[last]
    elif isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value
    return data


DELETE = object()


@pytest.mark.parametrize(
    "path, value, error",
    [
        ("format", "dancepose.motion.raw", RecordFormatError),
        ("fps", 0.0, RecordValueError),
        ("fps", True, RecordFormatError),
        ("width", 0, RecordValueError),
        ("width", 1.5, RecordFormatError),
        ("source", "", RecordFormatError),
        ("source", "a\nb", RecordFormatError),
        ("joint_names", list(reversed(JOINTS)), RecordValueError),
        ("bones", [[0, 1]] * 14, RecordValueError),
        ("cleaning", "smoothed", RecordFormatError),
        ("continuous_take", 1, RecordFormatError),
        ("frames", [], RecordValueError),
        ("frames.1.frame", 5, RecordValueError),
        ("frames.1.time", 9.0, RecordValueError),
        ("frames.1.xy", points()[:14], RecordFormatError),
        ("frames.1.xy.0", [1.0], RecordFormatError),
        ("frames.1.xy.0", [1e9, 1.0], RecordValueError),
        ("frames.1.xy.0", ["1", 1.0], RecordFormatError),
        ("frames.1.xy_stabilised.3", [-800.0, 1.0], RecordValueError),
        ("source_frame_end", 99, RecordValueError),
        ("source_time_s", [1.0], RecordFormatError),
        ("source_time_s", [5.0, 1.13], RecordValueError),
        ("duration_s", 9.0, RecordValueError),
        ("unknown", 1, RecordFormatError),
        ("frames.0.extra", 1, RecordFormatError),
        ("fps", DELETE, RecordFormatError),
        ("frames.0.xy", DELETE, RecordFormatError),
    ],
)
def test_a_malformed_or_inconsistent_record_is_refused_with_a_typed_error(path, value, error):
    with pytest.raises(error):
        pose_clean.from_data(mutate(path, value))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[]",
        "not json",
        json.dumps(record()).replace('"fps": 30.0', '"fps": NaN'),
        json.dumps(record()).replace('"fps": 30.0', '"fps": Infinity'),
        json.dumps(record()).replace('"fps": 30.0', '"fps": 30.0, "fps": 30.0'),
        b"\xff\xfe",
    ],
    ids=["empty", "array", "prose", "nan", "infinity", "repeated-key", "not-utf8"],
)
def test_text_that_is_not_one_strict_json_record_is_refused(text):
    with pytest.raises(pose_clean.PoseTrackError):
        pose_clean.parse(text)


def test_a_record_over_the_byte_limit_is_refused_before_it_is_decoded(monkeypatch):
    monkeypatch.setattr(pose_clean, "MAX_BYTES", 100)
    with pytest.raises(RecordFormatError, match="at most 100 bytes"):
        pose_clean.parse(json.dumps(record()))


def test_a_missing_file_is_a_format_error(tmp_path):
    with pytest.raises(RecordFormatError, match="cannot read"):
        pose_clean.load(tmp_path / "absent.json")


def test_load_reads_a_record_from_disk(tmp_path):
    path = tmp_path / "take.json"
    path.write_text(json.dumps(record()))
    assert pose_clean.load(path) == pose_clean.from_data(record())
