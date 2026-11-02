"""The srlocations bridge (ADR 0179): a blocking record made by ``tools/location_export.py`` in srlocations' own
interpreter, read here without srlocations. The fixture is a real run on the airliner catalog location at the reel's
portrait size; every other record in this file is that fixture broken on purpose, so each refusal is checked against
the one way a record can be wrong.
"""

import copy
import json
import math
import re
from pathlib import Path

import pytest

from srstudio import location_bridge as lb

FIXTURE = Path(__file__).resolve().parent / "data" / "location-bridge" / "airliner-1080x1920.json"
TEXT = FIXTURE.read_text()
DATA = json.loads(TEXT)


def broken(change) -> dict:
    """A copy of the fixture's data with ``change`` applied to it."""
    data = copy.deepcopy(DATA)
    change(data)
    return data


def first_mark(data: dict, shot: str = "down-the-aisle", mark: str = "aisle") -> dict:
    found = next(s for s in data["shots"] if s["name"] == shot)
    return next(m for m in found["marks"] if m["mark"] == mark)


# --- the record as recorded ---------------------------------------------------------------------------------------


def test_the_fixture_is_a_record_of_the_pinned_srlocations():
    record = lb.load(FIXTURE)
    assert record.schema_version == lb.SCHEMA_VERSION
    assert record.srlocations_commit == lb.SRLOCATIONS_COMMIT
    assert (record.location.source, record.location.name) == ("catalog", "airliner")
    assert re.fullmatch(r"[0-9a-f]{64}", record.location.digest)
    assert (record.frame.width, record.frame.height) == (1080, 1920)


def test_the_fixture_holds_at_least_two_shots_and_every_mark_in_each():
    record = lb.load(FIXTURE)
    assert len(record.shot_names) >= 2
    assert {"down-the-aisle", "window-seat"} <= set(record.shot_names)
    for name in record.shot_names:
        assert [m.name for m in record.shot(name).marks] == list(record.mark_names)
    assert "aisle" in record.mark_names


def test_a_mark_ahead_of_the_camera_gives_its_feet_and_scale():
    record = lb.load(FIXTURE)
    placed = record.placement("down-the-aisle", "aisle")
    mark = record.mark("down-the-aisle", "aisle")
    assert mark.feet == placed.feet and placed.scale == mark.pixels_per_metre > 0
    assert record.in_frame("down-the-aisle", "aisle") is mark.in_frame is True
    x, y = placed.feet
    assert 0 <= x <= 1080 and 0 <= y <= 1920


def test_the_camera_projects_any_point_as_srlocations_did():
    record = lb.load(FIXTURE)
    for name in record.shot_names:
        shot = record.shot(name)
        for mark in shot.marks:
            if mark.feet is not None:
                assert shot.camera.project(mark.at) == pytest.approx(mark.feet, abs=1e-6)
                assert shot.camera.pixels_per_metre(mark.at) == pytest.approx(mark.pixels_per_metre, rel=1e-9)
            else:
                assert shot.camera.project(mark.at) is None


def test_a_portrait_frame_fits_the_gate_to_its_height():
    camera = lb.load(FIXTURE).shot("down-the-aisle").camera
    assert camera.fit == "height"
    assert camera.focal_px == pytest.approx(camera.lens_mm * 1920 / 24.0)
    assert camera.fov_vertical_deg == pytest.approx(2 * math.degrees(math.atan(960 / camera.focal_px)))
    assert camera.fov_horizontal_deg == pytest.approx(2 * math.degrees(math.atan(540 / camera.focal_px)))
    assert camera.fov_horizontal_deg < camera.fov_vertical_deg


def test_a_point_behind_the_camera_has_no_pixel():
    camera = lb.load(FIXTURE).shot("down-the-aisle").camera
    behind = tuple(e - 2.0 * f for e, f in zip(camera.eye, camera.forward, strict=True))
    assert camera.depth(behind) < 0
    assert camera.project(behind) is None


def test_a_mark_behind_the_camera_has_no_placement():
    data = copy.deepcopy(DATA)
    del data["shots"][1:]
    shot = data["shots"][0]
    camera, eye = shot["camera"], shot["camera"]["eye_m"]
    assert shot["name"] == "down-the-aisle" and camera["forward"] == [0.0, 0.0, 1.0]
    # turn the first shot round: look the other way along z, so every mark ahead of it is now behind it
    camera["look_at_m"] = [eye[0], eye[1], eye[2] - 5.0]
    camera["right"] = [-camera["right"][0], camera["right"][1], -camera["right"][2]]
    camera["up"] = [-camera["up"][0], camera["up"][1], -camera["up"][2]]
    camera["forward"] = [-camera["forward"][0], camera["forward"][1], -camera["forward"][2]]
    focal = camera["focal_px"]
    for mark in shot["marks"]:
        mark.update(feet_px=None, head_px=None, in_frame=False, pixels_per_metre=focal / camera["near_m"])
    record = lb.from_data(data)
    assert record.mark(shot["name"], "aisle").feet is None
    assert record.in_frame(shot["name"], "aisle") is False
    with pytest.raises(lb.MarkNotVisibleError, match="aisle"):
        record.placement(shot["name"], "aisle")


def test_text_and_data_read_the_same_record():
    assert lb.parse(TEXT) == lb.parse(TEXT.encode()) == lb.from_data(DATA) == lb.load(FIXTURE)


def test_a_module_location_reads_with_its_own_digest():
    def module(data):
        data["location"] = {"source": "module", "name": "economy-row", "version": "0.1.0", "digest": "a" * 64}

    record = lb.from_data(broken(module))
    assert (record.location.source, record.location.catalog) == ("module", None)


def test_an_unknown_shot_or_mark_is_named():
    record = lb.load(FIXTURE)
    with pytest.raises(lb.UnknownShotError, match="down-the-aisle"):
        record.shot("cockpit")
    with pytest.raises(lb.UnknownMarkError, match="aisle"):
        record.mark("down-the-aisle", "seat-99c")


# --- malformed, incomplete and adversarial records -----------------------------------------------------------------


def _set(path, value):
    """A change that sets the field at ``path`` (keys and list indexes, with shots and marks found by name)."""

    def change(data):
        target = data
        for key in path[:-1]:
            if isinstance(key, tuple):
                kind, name = key
                target = next(item for item in target if item["name" if kind == "shot" else "mark"] == name)
            else:
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


SHOT, MARK = ("shot", "down-the-aisle"), ("mark", "aisle")

SHAPE = {
    "unknown top-level field": _set(["note"], "hello"),
    "unknown camera field": _set(["shots", SHOT, "camera", "roll_deg"], 0.0),
    "unknown mark field": _set(["shots", SHOT, "marks", MARK, "colour"], "red"),
    "missing frame": _drop(["frame"]),
    "missing marks": _drop(["shots", 0, "marks"]),
    "missing feet": _drop(["shots", 0, "marks", 0, "feet_px"]),
    "width as text": _set(["frame", "width_px"], "1080"),
    "width as a boolean": _set(["frame", "width_px"], True),
    "width as a float": _set(["frame", "width_px"], 1080.0),
    "in_frame as text": _set(["shots", SHOT, "marks", MARK, "in_frame"], "yes"),
    "lens as a boolean": _set(["shots", SHOT, "camera", "lens_mm"], True),
    "three feet coordinates": _set(["shots", SHOT, "marks", MARK, "feet_px"], [1.0, 2.0, 3.0]),
    "eye as an object": _set(["shots", SHOT, "camera", "eye_m"], {"x": 0, "y": 1, "z": 2}),
    "shots as an object": _set(["shots"], {"down-the-aisle": {}}),
    "a shot as a list": _set(["shots", 0], []),
    "commit as a number": _set(["srlocations_commit"], 2742),
    "a location source that is neither": _set(["location", "source"], "photo"),
    "a module source naming a catalog": _set(["location", "source"], "module"),
    "a fit that is neither": _set(["shots", SHOT, "camera", "fit"], "cover"),
    "a digest that is not sha256": _set(["location", "digest"], "301e57"),
    "a version that is not semver": _set(["location", "version"], "latest"),
    "an empty shot name": _set(["shots", 0, "name"], ""),
    "a control character in a mark name": _set(["shots", 0, "marks", 0, "mark"], "aisle\n"),
    "a frame too large to render": _set(["frame", "height_px"], 100_000),
    "no shots": _set(["shots"], []),
    "infinite feet": _set(["shots", SHOT, "marks", MARK, "feet_px"], [math.inf, 3.0]),
    "NaN scale": _set(["shots", SHOT, "marks", MARK, "pixels_per_metre"], math.nan),
}


@pytest.mark.parametrize("change", SHAPE.values(), ids=SHAPE.keys())
def test_a_record_of_the_wrong_shape_is_refused(change):
    with pytest.raises(lb.RecordFormatError):
        lb.from_data(broken(change))


def _shift_feet(data):
    feet = first_mark(data)["feet_px"]
    feet[0] += 5.0


def _duplicate_shot(data):
    data["shots"].append(copy.deepcopy(data["shots"][0]))


def _duplicate_mark(data):
    for shot in data["shots"]:
        shot["marks"].append(copy.deepcopy(shot["marks"][0]))


def _move_mark_in_one_shot(data):
    """Moves a mark in the second shot only, with its pixels, scale and in_frame moved to match that shot's camera:
    only the check across shots can find it."""
    shot = data["shots"][1]
    camera = lb.from_data(DATA).shot(shot["name"]).camera
    mark = shot["marks"][0]
    at = (mark["at_m"][0] + 0.5, mark["at_m"][1], mark["at_m"][2])
    feet, head = camera.project(at), camera.project((at[0], at[1] + mark["height_m"], at[2]))
    inside = bool(feet and head and 0 <= feet[0] <= 1080 and 0 <= head[1] <= 1920 and feet[1] >= 0)
    mark.update(
        at_m=list(at),
        feet_px=list(feet) if feet else None,
        head_px=list(head) if head else None,
        pixels_per_metre=camera.pixels_per_metre(at),
        in_frame=inside,
    )


def _drop_mark_in_one_shot(data):
    del data["shots"][1]["marks"][0]


def _bend_basis(data):
    camera = data["shots"][0]["camera"]
    camera["right"] = [camera["right"][0] * 1.1, camera["right"][1], camera["right"][2] * 1.1]


def _swap_basis(data):
    camera = data["shots"][0]["camera"]
    camera["right"] = [-value for value in camera["right"]]


def _aim_elsewhere(data):
    camera = data["shots"][0]["camera"]
    camera["look_at_m"] = [camera["look_at_m"][0] + 3.0, camera["look_at_m"][1], camera["look_at_m"][2]]


def _eye_on_target(data):
    camera = data["shots"][0]["camera"]
    camera["look_at_m"] = list(camera["eye_m"])


SEMANTIC = {
    "a mark in frame with no pixels": _set(["shots", SHOT, "marks", MARK, "feet_px"], None),
    "a mark in frame with no head": _set(["shots", SHOT, "marks", MARK, "head_px"], None),
    "in_frame claimed for a mark out of frame": _set(["shots", SHOT, "marks", MARK, "in_frame"], False),
    "feet moved off the projection": _shift_feet,
    "scale that is not positive": _set(["shots", SHOT, "marks", MARK, "pixels_per_metre"], -12.0),
    "scale off the projection": _set(["shots", SHOT, "marks", MARK, "pixels_per_metre"], 1.0),
    "a body with no height": _set(["shots", SHOT, "marks", MARK, "height_m"], 0.0),
    "a facing past a half turn": _set(["shots", SHOT, "marks", MARK, "facing_deg"], 270.0),
    "a lens of no length": _set(["shots", SHOT, "camera", "lens_mm"], 0.0),
    "a gate other than srlocations'": _set(["shots", SHOT, "camera", "gate_mm"], [35.0, 24.0]),
    "a fit the frame does not have": _set(["shots", SHOT, "camera", "fit"], "width"),
    "a focal length off the lens": _set(["shots", SHOT, "camera", "focal_px"], 100.0),
    "a near plane at the eye": _set(["shots", SHOT, "camera", "near_m"], 0.0),
    "a basis that is not unit length": _bend_basis,
    "a basis that is mirrored": _swap_basis,
    "a forward that does not look at the target": _aim_elsewhere,
    "an eye on its target": _eye_on_target,
    "a frame with no width": _set(["frame", "width_px"], 0),
    "two shots of one name": _duplicate_shot,
    "two marks of one name": _duplicate_mark,
    "a mark that moves between shots": _move_mark_in_one_shot,
    "a mark missing from one shot": _drop_mark_in_one_shot,
}


@pytest.mark.parametrize("change", SEMANTIC.values(), ids=SEMANTIC.keys())
def test_a_record_that_contradicts_itself_is_refused(change):
    with pytest.raises(lb.RecordValueError):
        lb.from_data(broken(change))


def test_a_mark_moved_in_one_shot_is_caught_across_shots():
    with pytest.raises(lb.RecordValueError, match="stands elsewhere"):
        lb.from_data(broken(_move_mark_in_one_shot))


@pytest.mark.parametrize("version", ["2.0.0", "0.9.0"])
def test_another_schema_major_is_refused(version):
    with pytest.raises(lb.SchemaVersionError, match=version):
        lb.from_data(broken(_set(["schema_version"], version)))


def test_a_later_minor_of_the_same_major_is_read():
    major, minor, _ = lb.SCHEMA_VERSION.split(".")
    assert lb.from_data(broken(_set(["schema_version"], f"{major}.{int(minor) + 1}.0"))).location.name == "airliner"


def test_a_schema_version_that_is_not_semver_is_a_format_error():
    with pytest.raises(lb.RecordFormatError):
        lb.from_data(broken(_set(["schema_version"], "1")))


def test_a_record_of_another_srlocations_commit_is_refused():
    other = "8dfe7a19d111763f321e72a8dafb1015ada0617a"
    with pytest.raises(lb.PinError, match=other):
        lb.from_data(broken(_set(["srlocations_commit"], other)))


SCALE = re.compile(r'"pixels_per_metre": [0-9.e+-]+')


def _scale_as(word: str) -> str:
    """The fixture's text with its first scale written as ``word``."""
    return SCALE.sub(f'"pixels_per_metre": {word}', TEXT, count=1)


@pytest.mark.parametrize(
    "text",
    [
        _scale_as("NaN"),
        _scale_as("Infinity"),
        _scale_as("-Infinity"),
        _scale_as("1e999"),
        TEXT[: len(TEXT) // 2],
        "",
        "[]",
        "null",
        b"\xff\xfe not utf-8",
        TEXT.replace('{\n "frame"', '{\n "frame": {"width_px": 1, "height_px": 1},\n "frame"', 1),
        " " * (lb.MAX_BYTES + 1),
    ],
    ids=[
        "NaN",
        "Infinity",
        "-Infinity",
        "overflow",
        "truncated",
        "empty",
        "list",
        "null",
        "bytes",
        "duplicate key",
        "oversize",
    ],
)
def test_text_that_is_not_one_strict_json_record_is_refused(text):
    with pytest.raises(lb.RecordFormatError):
        lb.parse(text)


def test_the_broken_texts_break_what_they_name():
    assert TEXT.startswith('{\n "frame"'), "the fixture is written with sorted keys, frame first"
    assert _scale_as("NaN") != TEXT and len(SCALE.findall(TEXT)) > 1
    with pytest.raises(lb.RecordFormatError, match="finite"):
        lb.parse(_scale_as("1e999"))
    with pytest.raises(lb.RecordFormatError, match="repeats"):
        lb.parse(TEXT.replace('{\n "frame"', '{\n "frame": {},\n "frame"', 1))


def test_every_refusal_is_one_typed_error():
    for error in (lb.RecordFormatError, lb.RecordValueError, lb.SchemaVersionError, lb.PinError):
        assert issubclass(error, lb.LocationRecordError)
    for error in (lb.LocationRecordError, lb.UnknownShotError, lb.UnknownMarkError, lb.MarkNotVisibleError):
        assert issubclass(error, lb.LocationBridgeError)


def test_a_missing_file_is_a_typed_error(tmp_path):
    with pytest.raises(lb.RecordFormatError, match="nothing"):
        lb.load(tmp_path / "nothing.json")
