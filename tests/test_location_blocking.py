"""Mannequin blocking in a location record (ADR 0184): srlocations' stock mannequin posed on marks by
``tools/location_export.py --blocking``, measured against the set, and read here without srlocations.

The fixture is a real export of the park at the reel's portrait size from the request beside it: a figure sitting on the
bench, its right hand reaching into the backrest, and a figure standing on the path, looking at the sitter and reaching
up. Every other record in this file is that fixture broken one way on purpose, and each is refused for the reason it
names.
"""

import copy
import json
import math
from pathlib import Path

import pytest

from srstudio import location_bridge as lb

DATA_DIR = Path(__file__).resolve().parent / "data" / "location-bridge"
FIXTURE = DATA_DIR / "park-blocking-1080x1920.json"
REQUEST = DATA_DIR / "park-blocking.request.json"
AIRLINER = DATA_DIR / "airliner-1080x1920.json"
TEXT = FIXTURE.read_text()
DATA = json.loads(TEXT)


def broken(change) -> dict:
    data = copy.deepcopy(DATA)
    change(data)
    return data


def figure(data: dict, mark: str) -> dict:
    return next(item for item in data["blocking"]["figures"] if item["mark"] == mark)


def pixels(data: dict, mark: str, shot: str) -> dict:
    return next(item for item in figure(data, mark)["shots"] if item["shot"] == shot)


def camera(shot: str) -> lb.Camera:
    return lb.from_data(DATA).shot(shot).camera


# --- the record as exported ----------------------------------------------------------------------------------------


def test_the_fixture_is_a_blocking_record_of_the_pinned_srlocations():
    record = lb.load(FIXTURE)
    assert record.schema_version == lb.SCHEMA_VERSION == "1.1.0"
    assert record.srlocations_commit == lb.SRLOCATIONS_COMMIT
    assert (record.location.name, record.frame) == ("park", lb.Frame(1080, 1920))
    assert record.blocked is not None and record.blocked.marks == ("bench", "walker")
    assert record.blocked.points.keys() == lb.parse_request(REQUEST.read_text()).points.keys()


def test_the_fixture_holds_what_its_request_asked():
    request = lb.parse_request(REQUEST.read_bytes())
    record = lb.load(FIXTURE)
    for asked in request.figures:
        assert record.blocked_figure(asked.mark).request == asked


def test_a_seated_figure_reports_the_seat_it_took_and_what_carries_it():
    record = lb.load(FIXTURE)
    sitter = record.blocked_figure("bench")
    assert sitter.sits and sitter.request.posture == "sit"
    assert sitter.seat is not None and sitter.seat.part in record.blocked.set_parts
    assert sitter.seat.back_m > 0 and sitter.back_rests is not None
    assert {s.joint for s in sitter.support if s.way == "down"} == {"hips", "left_upper_leg", "right_upper_leg"}
    assert sitter.carried is True
    assert sitter.facing_deg == pytest.approx(sitter.seat.facing_deg)


def test_a_standing_figure_has_no_seat_and_stands_on_its_feet():
    record = lb.load(FIXTURE)
    walker = record.blocked_figure("walker")
    assert not walker.sits and walker.seat is None and walker.back_rests is None
    assert walker.carried is True and any(s.joint.endswith("_foot") and s.rests for s in walker.support)
    assert walker.off_mark_m < 0.05
    (reached,) = walker.reached
    assert (reached.joint, reached.to) == ("right_hand", "wave") and reached.missed_m <= lb.REACH_TOLERANCE_M


def test_hands_and_shoulders_are_named_on_the_figures_own_sides():
    for item in lb.load(FIXTURE).blocked.figures:
        turn = math.radians(item.facing_deg)
        right = (math.cos(turn), 0.0, -math.sin(turn))
        left_shoulder, right_shoulder = item.shoulders
        assert sum((r - le) * w for r, le, w in zip(right_shoulder, left_shoulder, right, strict=True)) > 0
        for side, hand in zip(("left", "right"), item.hands, strict=True):
            shoulder = item.joints[f"{side}_upper_arm"]
            assert math.dist(hand, shoulder) <= item.arm_reach_m + 1e-9


def test_every_pixel_is_the_shots_camera_on_the_metres():
    record = lb.load(FIXTURE)
    for shot in record.shot_names:
        view = record.shot(shot).camera
        for item in record.blocked.figures:
            placed = record.blocking(shot, item.mark)
            for name in lb.BODY_JOINTS:
                expected = view.project(item.joints[name])
                assert placed.joint(name) == (None if expected is None else pytest.approx(expected, abs=1e-6))
            assert placed.pixels.pixels_per_metre == pytest.approx(view.pixels_per_metre(item.at))


def test_a_shot_from_behind_gives_no_pixels():
    record = lb.load(FIXTURE)
    placed = record.blocking("along-the-path", "walker")
    assert all(px is None for px in placed.pixels.joints.values())


def test_the_pose_repeats_as_srlocations_writes_it():
    sitter = lb.load(FIXTURE).blocked_figure("bench")
    spec = sitter.pose_spec
    assert spec["sits"] is True and spec["controls"] == dict(sorted(sitter.controls.items()))
    assert all(lb.PARAMETER.fullmatch(key) for key in sitter.controls)


def test_a_record_without_blocking_still_reads_and_says_it_has_none():
    record = lb.load(AIRLINER)
    assert record.schema_version == "1.0.0" and record.blocked is None
    with pytest.raises(lb.NoBlockingError, match="no blocking"):
        record.blocking("down-the-aisle", "aisle")
    with pytest.raises(lb.NoBlockingError, match="no blocking"):
        record.require_clear()


def test_an_unknown_mark_or_shot_is_named():
    record = lb.load(FIXTURE)
    with pytest.raises(lb.NoBlockingError, match="walker"):
        record.blocked_figure("lamp-post")
    with pytest.raises(lb.UnknownShotError):
        record.blocking("from-the-moon", "walker")
    with pytest.raises(lb.UnknownMarkError, match="head"):
        record.blocking("over-the-lawn", "walker").joint("nose")


# --- the gate ------------------------------------------------------------------------------------------------------


def test_the_gate_passes_a_clear_carried_body():
    lb.load(FIXTURE).require_clear("walker")


def test_the_gate_refuses_a_hand_in_the_backrest_naming_limb_and_part():
    record = lb.load(FIXTURE)
    sitter = record.blocked_figure("bench")
    assert [clash.limb for clash in sitter.clashes] == ["right_upper_arm", "right_lower_arm", "right_hand"]
    with pytest.raises(lb.BlockingClashError, match=r"bench: right_hand is [0-9.]+ cm inside park/") as refused:
        record.require_clear("bench")
    for clash in sitter.clashes:
        assert f"bench: {clash.limb} is {clash.depth_m * 100:.1f} cm inside {clash.part}" in str(refused.value)
        assert clash.part in record.blocked.set_parts and clash.depth_m > 0 and not clash.buried
    with pytest.raises(lb.BlockingClashError):
        record.require_clear()


def test_the_gate_refuses_a_body_tangled_in_itself():
    def tangle(data):
        figure(data, "walker")["tangled"] = [{"limb": "left_hand", "other": "chest"}]

    with pytest.raises(lb.BlockingClashError, match="walker: left_hand passes through chest"):
        lb.from_data(broken(tangle)).require_clear("walker")


def _float(data):
    """The walker lifted off its feet: every foot's gap past the rest, and nothing carrying it."""
    walker = figure(data, "walker")
    for support in walker["support"]:
        support.update(gap_m=0.05, rests=False)
    walker["carried"] = False


def test_the_gate_refuses_a_body_nothing_carries_unless_asked_not_to():
    record = lb.from_data(broken(_float))
    with pytest.raises(lb.BlockingSupportError, match="walker"):
        record.require_clear("walker")
    record.require_clear("walker", carried=False)


def test_every_gate_refusal_is_one_typed_error():
    for error in (lb.NoBlockingError, lb.BlockingClashError, lb.BlockingSupportError):
        assert issubclass(error, lb.BlockingError) and issubclass(error, lb.LocationBridgeError)
    assert issubclass(lb.RequestError, lb.LocationBridgeError)


# --- the request ---------------------------------------------------------------------------------------------------


def test_a_request_reads_and_writes_itself_back():
    request = lb.parse_request(REQUEST.read_text())
    assert [f.mark for f in request.figures] == ["bench", "walker"]
    assert request.figures[0].pose == "sit" and request.figures[1].pose == "stand"
    assert lb.parse_request(request.to_json()) == request
    assert json.loads(request.to_json())["schema_version"] == lb.REQUEST_VERSION


REQUEST_DATA = json.loads(REQUEST.read_text())


def _req(change) -> str:
    data = copy.deepcopy(REQUEST_DATA)
    change(data)
    return json.dumps(data)


def _set_figure(key, value, index=0):
    def change(data):
        data["figures"][index][key] = value

    return change


BAD_REQUESTS = {
    "unknown field": (lambda d: d.update(note="hi"), "unknown field"),
    "unknown figure field": (_set_figure("mood", "happy"), "unknown field"),
    "missing posture": (lambda d: d["figures"][0].pop("posture"), "lacks"),
    "a posture that is neither": (_set_figure("posture", "lie"), "'stand' or 'sit'"),
    "a reach with the head": (_set_figure("reach", [{"joint": "head", "to": "wave"}]), "left_hand"),
    "a reach to no point": (_set_figure("reach", [{"joint": "left_hand", "to": "moon"}]), "moon"),
    "a look at no point": (_set_figure("look_at", "moon"), "moon"),
    "a limb reaching twice": (
        _set_figure("reach", [{"joint": "left_hand", "to": "wave"}, {"joint": "left_hand", "to": "sitter"}]),
        "twice",
    ),
    "two figures on one mark": (lambda d: d["figures"].append(copy.deepcopy(d["figures"][0])), "one figure to a mark"),
    "no figures": (lambda d: d.update(figures=[]), "at least one"),
    "a height of nothing": (_set_figure("height_m", 0.0), "above 0"),
    "a height past a body": (_set_figure("height_m", 3.5), "at most 3.0"),
    "a height as text": (_set_figure("height_m", "tall"), "number"),
    "a seed as a boolean": (_set_figure("seed", True), "whole number"),
    "a negative seed": (_set_figure("seed", -1), "from 0"),
    "a pose name with a space": (_set_figure("pose", "sit down"), "must match"),
    "an adjust key with no control": (_set_figure("adjust", {"head": 10}), "must match"),
    "an adjust angle as text": (_set_figure("adjust", {"head.turn_left_right": "10"}), "number"),
    "a point of two numbers": (lambda d: d["points"].update(wave=[1.0, 2.0]), "3 numbers"),
    "another request major": (lambda d: d.update(schema_version="2.0.0"), "2.0.0"),
    "too many figures": (
        lambda d: d.update(figures=[{"mark": f"m{i}", "posture": "stand"} for i in range(lb.MAX_FIGURES + 1)]),
        "at most",
    ),
}


@pytest.mark.parametrize(("change", "reason"), BAD_REQUESTS.values(), ids=BAD_REQUESTS.keys())
def test_a_bad_request_is_refused_for_its_reason(change, reason):
    with pytest.raises(lb.RequestError, match=reason):
        lb.parse_request(_req(change))


@pytest.mark.parametrize(
    "text",
    [REQUEST.read_text().replace("1.83", "NaN"), "[]", "", b"\xff", '{"a": 1, "a": 2}'],
    ids=["NaN", "list", "empty", "bytes", "repeated key"],
)
def test_request_text_that_is_not_strict_json_is_refused(text):
    with pytest.raises(lb.RequestError):
        lb.parse_request(text)


# --- malformed and incomplete blocking -----------------------------------------------------------------------------


def _blk(*path, value):
    """A change that sets a field of the blocking section; a path that starts with a mark goes into that figure."""

    def change(data):
        target = figure(data, path[0]) if path[0] in ("bench", "walker") else data["blocking"]
        for key in path[1 if path[0] in ("bench", "walker") else 0 : -1]:
            target = target[key]
        target[path[-1]] = value

    return change


def _too_many_points(data):
    data["blocking"]["points"] = {f"p{index}": [0.0, 0.0, 0.0] for index in range(65)}


SHAPE = {
    "an unknown blocking field": (_blk("note", value=1), "unknown field"),
    "points as a list": (_blk("points", value=[[0.0, 0.0, 0.0]]), "JSON object of named points"),
    "too many points": (_too_many_points, "at most 64 points"),
    "pose controls as a list": (lambda d: figure(d, "walker")["pose"].update(controls=[]), "object of pose controls"),
    "an unknown figure field": (_blk("walker", "mood", value="calm"), "unknown field"),
    "a joint missing": (lambda d: figure(d, "walker")["joints_m"].pop("left_hand"), "lacks"),
    "an extra joint": (_blk("walker", "joints_m", "nose", value=[0, 0, 0]), "unknown field"),
    "a joint pixel of three numbers": (
        lambda d: figure(d, "walker")["shots"][3]["joints_px"].update(head=[1.0, 2.0, 3.0]),
        "at most 2 items",
    ),
    "a joint pixel of one number": (
        lambda d: figure(d, "walker")["shots"][3]["joints_px"].update(head=[1.0]),
        "2 numbers",
    ),
    "carried as text": (_blk("walker", "carried", value="yes"), "true or false"),
    "back_rests as a number": (_blk("walker", "back_rests", value=1), "true, false or null"),
    "a clash depth that is NaN": (
        _blk(
            "bench",
            "clashes",
            value=[{"limb": "right_hand", "part": "park/part-0", "depth_m": math.nan, "buried": False}],
        ),
        "finite",
    ),
    "a support way that is neither": (lambda d: figure(d, "walker")["support"][0].update(way="up"), "'down' or 'back'"),
    "a limit bound that is neither": (
        _blk(
            "walker",
            "at_limit",
            value=[{"control": "head.nod_down_up", "value_deg": 1, "bound": "max", "bound_deg": 1}],
        ),
        "'low' or 'high'",
    ),
    "too many set parts": (_blk("set_parts", value=[f"p{i}" for i in range(lb.MAX_SET_PARTS + 1)]), "at most"),
    "too many controls": (
        lambda d: figure(d, "walker")["pose"]["controls"].update({f"hips.c{i}": 0.0 for i in range(lb.MAX_CONTROLS)}),
        "at most",
    ),
    "a part path with a newline": (_blk("set_parts", value=["park/part-0\n"]), "printable"),
    "a reach with the head": (lambda d: figure(d, "walker")["reached"][0].update(joint="head"), "left_hand"),
    "a seat with no back field": (lambda d: figure(d, "bench")["seat"].pop("back_m"), "lacks"),
    "blocking in a 1.0.0 record": (lambda d: d.update(schema_version="1.0.0"), "1.1.0"),
}


@pytest.mark.parametrize(("change", "reason"), SHAPE.values(), ids=SHAPE.keys())
def test_blocking_of_the_wrong_shape_is_refused_for_its_reason(change, reason):
    with pytest.raises(lb.RecordFormatError, match=reason):
        lb.from_data(broken(change))


# --- blocking that contradicts itself, its camera or its set -------------------------------------------------------


def _move_pixel(data):
    pixels(data, "walker", "over-the-lawn")["joints_px"]["head"][0] += 4.0


def _pixel_behind(data):
    pixels(data, "walker", "along-the-path")["joints_px"]["head"] = [540.0, 960.0]


def _no_pixel_in_front(data):
    pixels(data, "walker", "over-the-lawn")["joints_px"]["left_hand"] = None


def _swap(data, mark, a, b):
    """Swaps two joints, metres and every shot's pixels together, so only the side check can tell."""
    item = figure(data, mark)
    item["joints_m"][a], item["joints_m"][b] = item["joints_m"][b], item["joints_m"][a]
    for shot in item["shots"]:
        shot["joints_px"][a], shot["joints_px"][b] = shot["joints_px"][b], shot["joints_px"][a]


def _turn_around(data):
    """The walker said to face the other way, its pixels and every number but its facing left as they were."""
    item = figure(data, "walker")
    item["facing_deg"] = item["facing_deg"] - 180.0 if item["facing_deg"] > 0 else item["facing_deg"] + 180.0


def _stand_the_sitter(data):
    item = figure(data, "bench")
    item["seat"] = None
    for shot in item["shots"]:
        shot["seat_px"] = None


def _seat_the_walker(data):
    walker, sitter = figure(data, "walker"), figure(data, "bench")
    walker["seat"] = copy.deepcopy(sitter["seat"])


def _rename_part(mark, field, value):
    def change(data):
        figure(data, mark)[field][0]["part"] = value

    return change


def _seat_part(data):
    figure(data, "bench")["seat"]["part"] = "park/sofa"


def _shift_reach(data):
    figure(data, "walker")["reached"][0]["missed_m"] = 0.004


def _wrong_carried(data):
    figure(data, "walker")["carried"] = False


def _wrong_rests(data):
    figure(data, "walker")["support"][0]["rests"] = False


def _wrong_back(data):
    item = figure(data, "bench")
    item["back_rests"] = not item["back_rests"]


def _null_part_close(data):
    figure(data, "walker")["support"][0]["part"] = None


def _limit_not_in_pose(data):
    figure(data, "walker")["at_limit"] = [
        {"control": "head.nod_down_up", "value_deg": 20.0, "bound": "high", "bound_deg": 20.0}
    ]


def _off_mark(data):
    figure(data, "walker")["off_mark_m"] = 0.5


def _unknown_mark(data):
    item = figure(data, "walker")
    item["mark"] = item["request"]["mark"] = "fountain"


def _two_on_one_mark(data):
    data["blocking"]["figures"].append(copy.deepcopy(figure(data, "walker")))


def _drop_a_shot(data):
    figure(data, "walker")["shots"].pop()


def _scale_off(data):
    pixels(data, "walker", "over-the-lawn")["pixels_per_metre"] *= 1.5


def _seat_pixel_off(data):
    pixels(data, "bench", "over-the-lawn")["seat_px"][1] += 3.0


def _sight_far(data):
    item = figure(data, "walker")
    eye, ahead = item["sight_m"]["eye"], item["sight_m"]["ahead"]
    item["sight_m"]["ahead"] = [e + 2.0 * (a - e) for e, a in zip(eye, ahead, strict=True)]
    for shot in item["shots"]:
        view = camera(shot["shot"])
        found = view.project(tuple(item["sight_m"]["ahead"]))
        shot["sight_px"]["ahead"] = None if found is None else list(found)


def _sits_as_walker(data):
    figure(data, "walker")["pose"]["sits"] = True


def _strange_control(data):
    figure(data, "walker")["pose"]["controls"]["tail.wag"] = 10.0


def _short_skeleton(data):
    data["blocking"]["skeleton"].remove("left_hand")


def _seat_turned(data):
    figure(data, "bench")["seat"]["facing_deg"] += 30.0


def _clash_limb(data):
    figure(data, "bench")["clashes"][0]["limb"] = "tail"


def _request_mark(data):
    figure(data, "walker")["request"]["mark"] = "bench"


def _contact_backwards(data):
    data["blocking"]["contact"]["rest_m"] = 0.5


def _swap_free_hands(data):
    """With no reach to contradict them, only the arm's length of each hand from its own shoulder can tell."""
    item = figure(data, "bench")
    item["reached"] = item["request"]["reach"] = []
    _swap(data, "bench", "left_hand", "right_hand")


def _dropped_adjust(data):
    figure(data, "walker")["request"]["adjust"] = {"head.tilt_left_right": 5.0}


def _repeat(field):
    def change(data):
        data["blocking"][field].append(data["blocking"][field][0])

    return change


def _sets(mark, **fields):
    def change(data):
        figure(data, mark).update(fields)

    return change


def _sets_seat(**fields):
    def change(data):
        figure(data, "bench")["seat"].update(fields)

    return change


def _sets_support(**fields):
    def change(data):
        figure(data, "walker")["support"][0].update(fields)

    return change


def _point_gone(data):
    del data["blocking"]["points"]["sitter"]


def _control(data):
    return next(iter(figure(data, "walker")["pose"]["controls"].items()))


def _limit(data, value, bound):
    control, _ = _control(data)
    return {"control": control, "value_deg": value, "bound": "high", "bound_deg": bound}


def _limit_twice(data):
    value = _control(data)[1]
    figure(data, "walker")["at_limit"] = [_limit(data, value, value), _limit(data, value, value)]


def _limit_off_its_bound(data):
    value = _control(data)[1]
    figure(data, "walker")["at_limit"] = [_limit(data, value, value + 5.0)]


def _limit_on_no_control(data):
    figure(data, "walker")["at_limit"] = [
        {"control": "head.no_such_control", "value_deg": 5.0, "bound": "high", "bound_deg": 5.0}
    ]


def _clash_twice(data):
    item = figure(data, "bench")
    item["clashes"].append(copy.deepcopy(item["clashes"][0]))


def _clash(data, **fields):
    figure(data, "bench")["clashes"][0].update(fields)


def _no_seat_contact(data):
    """A sitter with its seat on record and nothing under it: the part is gone from the seat and from its hips."""
    item = figure(data, "bench")
    item["seat"]["part"] = None
    hips = next(s for s in item["support"] if s["joint"] == "hips")
    hips.update(gap_m=data["blocking"]["contact"]["gap_m"], part=None, rests=False)
    item["carried"] = False


def _back_on_a_stander(data):
    figure(data, "walker")["support"].append(
        {"joint": "chest", "way": "back", "gap_m": 0.1, "part": "park/path", "rests": False}
    )


def _no_back_on_a_backed_seat(data):
    item = figure(data, "bench")
    item["support"] = [s for s in item["support"] if s["way"] != "back"]


def _seat_pixel_on_a_stander(data):
    figure(data, "walker")["shots"][3]["seat_px"] = [1.0, 2.0]


SEMANTIC = {
    "a joint pixel off the camera": (_move_pixel, "the camera puts it"),
    "a pixel for a joint behind the camera": (_pixel_behind, "behind the camera"),
    "no pixel for a joint in front of the camera": (_no_pixel_in_front, "in front of the camera"),
    "shoulders swapped": (lambda d: _swap(d, "walker", "left_upper_arm", "right_upper_arm"), "own right"),
    "eyes swapped": (lambda d: _swap(d, "bench", "left_eye", "right_eye"), "own right"),
    "hands swapped on a reaching limb": (lambda d: _swap(d, "bench", "left_hand", "right_hand"), "a reach misses"),
    "hands swapped with no reach": (_swap_free_hands, "past an arm"),
    "a facing turned around": (_turn_around, "own right"),
    "a sitter with no seat": (_stand_the_sitter, "reports no seat"),
    "a stander with a seat": (_seat_the_walker, "reports a seat"),
    "a clash with no part of the set": (_rename_part("bench", "clashes", "park/sofa"), "not a part of the set"),
    "a support on no part of the set": (_rename_part("walker", "support", "park/sofa"), "not a part of the set"),
    "a seat that is no part of the set": (_seat_part, "not a part of the set"),
    "a clash by no limb": (_clash_limb, "not in the skeleton"),
    "a reach missed by other than its distance": (_shift_reach, "recorded as missed"),
    "carried against its supports": (_wrong_carried, "carried=False"),
    "rests against its gap": (_wrong_rests, "rests=False"),
    "back_rests against its gaps": (_wrong_back, "back_rests="),
    "no part under a limb that met one": (_null_part_close, "with None under it"),
    "a limit the pose does not hold": (_limit_not_in_pose, "not in the pose"),
    "off its mark by other than its distance": (_off_mark, "off its mark"),
    "a figure on no mark of the record": (_unknown_mark, "no mark 'fountain'"),
    "two figures on one mark": (_two_on_one_mark, "one body to a mark"),
    "pixels for fewer shots": (_drop_a_shot, "pixels for shots"),
    "a scale off the camera": (_scale_off, "px per metre"),
    "a seat pixel off the camera": (_seat_pixel_off, "its seat is at"),
    "a sight point two metres out": (_sight_far, "not 1 m"),
    "a stander whose pose sits": (_sits_as_walker, "the request asks to stand"),
    "a control on no joint of the skeleton": (_strange_control, "not in the skeleton"),
    "a skeleton without a recorded joint": (_short_skeleton, "lacks the recorded joint"),
    "a sitter turned from its seat": (_seat_turned, "and its seat"),
    "a request for another mark": (_request_mark, "the request poses mark"),
    "a rest past the probe": (_contact_backwards, "rest is under"),
    "an adjust the pose dropped": (_dropped_adjust, "does not hold them"),
    "a skeleton that repeats a joint": (_repeat("skeleton"), "skeleton joints repeat"),
    "set parts that repeat": (_repeat("set_parts"), "set parts repeat"),
    "a request naming a point the record lacks": (_point_gone, "the record does not hold"),
    "a facing past half a turn": (_sets("walker", facing_deg=200.0), "half a turn"),
    "a stature past a body": (_sets("walker", stature_m=4.0), "a stature of 4.0"),
    "an arm longer than the body": (_sets("walker", arm_reach_m=2.0), "an arm of 2.0"),
    "an arm of nothing": (_sets("walker", arm_reach_m=0.0), "an arm of 0.0"),
    "a limit listed twice": (_limit_twice, "listed at its limit twice"),
    "a limit off its bound": (_limit_off_its_bound, "is not at its high"),
    "a limit on no control": (_limit_on_no_control, "not in the pose"),
    "a reach the record dropped": (_sets("walker", reached=[]), "not what the request asks"),
    "a seat below the ground": (_sets_seat(height_m=-0.1), "0 or more"),
    "a seat that is not under the hips": (_sets_seat(part="park/part-1392"), "under the hips is"),
    "a sitter with no seat contact": (_no_seat_contact, "meet no part of the set"),
    "a clash listed twice": (_clash_twice, "listed twice"),
    "a clash of negative depth": (lambda d: _clash(d, depth_m=-0.01), "m deep"),
    "a buried clash with a depth": (lambda d: _clash(d, buried=True), "m deep"),
    "a limb through itself": (_sets("walker", tangled=[{"limb": "chest", "other": "chest"}]), "names no two"),
    "a tangle with no limb": (_sets("walker", tangled=[{"limb": "chest", "other": "tail"}]), "names no two"),
    "a support by no joint": (_sets_support(joint="tail"), "not in the skeleton"),
    "a gap below nothing": (_sets_support(gap_m=-0.1), "a gap is 0 to"),
    "a gap past the probe": (_sets_support(gap_m=0.31), "a gap is 0 to"),
    "no limb carrying it": (_sets("walker", support=[]), "no limb says"),
    "a back measured on a stander": (_back_on_a_stander, "only for a seat with a back"),
    "no back measured on a backed seat": (_no_back_on_a_backed_seat, "only for a seat with a back"),
    "a seat pixel on a stander": (_seat_pixel_on_a_stander, "a seat pixel for a body with no seat"),
}


@pytest.mark.parametrize(("change", "reason"), SEMANTIC.values(), ids=SEMANTIC.keys())
def test_blocking_that_contradicts_itself_is_refused_for_its_reason(change, reason):
    with pytest.raises(lb.RecordValueError, match=reason):
        lb.from_data(broken(change))


@pytest.mark.parametrize(("change", "reason"), SEMANTIC.values(), ids=SEMANTIC.keys())
def test_only_the_semantic_checks_catch_each_contradiction(change, reason, monkeypatch):
    """With the blocking checks switched off every case above reads: each is well formed, and it is the semantic check
    that refuses it, not the parse."""
    monkeypatch.setattr(lb, "_check_blocking", lambda record: None)
    assert lb.from_data(broken(change)).blocked is not None


def test_a_control_at_its_limit_reads_and_says_so():
    def limited(data):
        figure(data, "walker")["at_limit"] = [_limit(data, _control(data)[1], _control(data)[1])]

    data = broken(limited)
    assert [hit.control for hit in lb.from_data(data).blocked_figure("walker").at_limit] == [_control(data)[0]]


def test_a_buried_limb_has_no_depth_and_the_gate_says_buried():
    record = lb.from_data(broken(lambda d: _clash(d, buried=True, depth_m=0.0)))
    with pytest.raises(lb.BlockingClashError, match=r"bench: right_upper_arm is buried in park/"):
        record.require_clear("bench")


def test_the_swapped_hands_are_far_enough_apart_to_tell():
    sitter = lb.load(FIXTURE).blocked_figure("bench")
    assert math.dist(sitter.joints["left_hand"], sitter.joints["right_upper_arm"]) > sitter.arm_reach_m
