"""The Stick airport: the gate with its window, plane and boarding sign, the podium in front of the agent, the
carry-on with its group tag, the cabin row with its seats and armrests, the seated poses that fit them, and the
pilot's cap a look can wear."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, fonts, registry, stick, stick_airport
from srstudio.canvas import Signature
from srstudio.sample import SYSTEM_FONTS
from srstudio.stick import StickDataError

WIDE_BOLD = next((f for f in SYSTEM_FONTS if f.exists()), None)
needs_font = pytest.mark.skipif(WIDE_BOLD is None, reason="DejaVu Sans Bold is required")


def canvas(font: str | None = "inter") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset=font, namer=flat_counter("n"), signature=Signature())


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list[str]:
    return [t.get("text") for t in xml(cv).iter("text")]


def shapes(cv: Canvas) -> int:
    return len(list(xml(cv).iter("shape")))


def test_the_parts_are_registered_for_the_stick_style():
    for kind, name in (("location", "stick-gate"), ("prop", "stick-gate-podium"), ("prop", "stick-carry-on"),
                       ("location", "stick-cabin"), ("prop", "stick-armrests"), ("prop", "stick-bag-scale"),
                       ("prop", "stick-coat-ball"), ("prop", "stick-palm")):  # fmt: skip
        assert registry.get(kind, name).style == "stick"


def test_the_gate_letters_its_sign_and_signs_its_floor():
    cv = canvas()
    stick_airport.gate(cv, cv.comp, gate="B9", now="GROUP 4")
    assert {"B9", "NOW BOARDING", "GROUP 4"} <= set(texts(cv))
    assert shapes(cv) > 30
    assert any("sig-code" in (g.get("id") or "") for g in xml(cv).iter())


@needs_font
def test_the_signs_first_line_fits_beside_the_gate_letters():
    assert WIDE_BOLD is not None
    width = stick_airport.SIGN_BOX[2] - 170
    assert fonts.text_width(WIDE_BOLD.read_bytes(), "NOW BOARDING", stick_airport.BOARDING_SIZE) <= width


@pytest.mark.parametrize(
    ("kw", "size"),
    [
        ({}, str(stick_airport.APPROVED_BOARDING_SIZE)),
        ({"boarding_size": stick_airport.BOARDING_SIZE}, str(stick_airport.BOARDING_SIZE)),
    ],
)
def test_the_default_sign_is_the_approved_drawing_and_a_reel_can_ask_for_the_fitted_size(kw, size):
    cv = canvas()
    stick_airport.gate(cv, cv.comp, gate="B9", now="GROUP 4", **kw)
    assert [t.get("size") for t in xml(cv).iter("text") if t.get("text") == "NOW BOARDING"] == [size]


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(gate=""), "gate"),
        (dict(gate="B999X"), "gate"),
        (dict(boarding_size=0), "size"),
        (dict(now=""), "sign"),
        (dict(now="X" * (stick_airport.NOW_CHARS + 1)), "sign"),
    ],
)
def test_the_gate_refuses_a_sign_it_cannot_letter(kw, match):
    cv = canvas()
    with pytest.raises(StickDataError, match=match):
        stick_airport.gate(cv, cv.comp, **kw)


def test_the_gate_needs_the_caption_font():
    cv = canvas(font=None)
    with pytest.raises(ValueError, match="font"):
        stick_airport.gate(cv, cv.comp)


def test_the_podium_stands_in_front_of_the_agent_at_the_right():
    cv = canvas()
    stick_airport.podium(cv, cv.comp, gate="B9")
    assert "B9" in texts(cv)
    xs = [float(r.get("x")) for r in xml(cv).iter("shape") if r.get("x") is not None]
    assert xs and min(xs) >= stick_airport.PODIUM_X[0] - 1


def test_the_carry_on_hangs_its_tag_and_refuses_a_long_one():
    cv = canvas()
    stick_airport.carry_on(cv, cv.comp, 480, stick_airport.FLOOR_FEET, tag="GROUP 4")
    assert "GROUP 4" in texts(cv)
    with pytest.raises(StickDataError, match="tag"):
        stick_airport.carry_on(cv, cv.comp, 480, stick_airport.FLOOR_FEET, tag="X" * (stick_airport.TAG_CHARS + 1))


def test_the_cabin_labels_its_row_and_seats():
    cv = canvas()
    stick_airport.cabin(cv, cv.comp, row="38", seats="DEF")
    shown = texts(cv)
    assert "38" in shown and {"D", "E", "F"} <= set(shown)
    with pytest.raises(StickDataError, match="row"):
        stick_airport.cabin(cv, cv.comp, row="")
    with pytest.raises(StickDataError, match="seats"):
        stick_airport.cabin(cv, cv.comp, seats="DE")


def test_the_armrests_sit_between_the_seats():
    cv = canvas()
    stick_airport.armrests(cv, cv.comp)
    xs = [float(r.get("x")) for r in xml(cv).iter("shape") if r.get("x") is not None]
    for x in stick_airport.ARMRESTS:
        assert any(abs(v - (x - stick_airport.ARMREST_W / 2)) < 1 for v in xs)


def test_the_seated_poses_draw_and_the_neighbours_take_both_armrests():
    for name in stick_airport.SQUEEZED:
        cv = canvas()
        stick.rig(cv, cv.comp, [stick.RigKey(0, name)], 2.0, poses=stick_airport.SQUEEZED)
    spread = stick_airport.SQUEEZED["spread"]
    left, right = stick_airport.ARMRESTS
    offset = stick_airport.SEAT_STEP
    # the passenger one seat left rests the near elbow on the left armrest; the one right, the far elbow on the right
    assert abs(spread.elbows[1][0] - offset - left) < 20
    assert abs(spread.elbows[0][0] + offset - right) < 20
    middle = stick_airport.SQUEEZED["tucked"]
    assert left < min(x for x, _ in middle.elbows) and max(x for x, _ in middle.elbows) < right


def test_the_agent_stands_behind_the_podium():
    hip = stick.STANDING["stand"].hip
    x = stick_airport.AGENT_AT[0] - hip[0]  # flipped about the agent's mark
    assert stick_airport.PODIUM_X[0] < x < stick_airport.PODIUM_X[1]
    assert stick_airport.PODIUM_TOP < hip[1]


def test_a_look_can_wear_a_cap_and_the_default_is_unchanged():
    plain, also_plain, capped = canvas(), canvas(), canvas()
    key = [stick.RigKey(0, "stand")]
    stick.rig(plain, plain.comp, key, 2.0, poses=stick.STANDING)
    stick.rig(also_plain, also_plain.comp, key, 2.0, poses=stick.STANDING, look=stick.Look(cap=None))
    stick.rig(capped, capped.comp, key, 2.0, poses=stick.STANDING, look=stick.Look(cap="#1f2a44"))
    assert plain.scene.to_bytes(layout="pretty") == also_plain.scene.to_bytes(layout="pretty")
    assert shapes(capped) > shapes(plain)
    with pytest.raises(StickDataError, match="cap"):
        stick.check_look(stick.Look(cap="navy"))


def test_a_close_up_can_leave_the_plate_and_the_tag_unlettered():
    cv = canvas()
    stick_airport.podium(cv, cv.comp, gate="B9", plate=False)
    stick_airport.carry_on(cv, cv.comp, 480, stick_airport.FLOOR_FEET, tag=None)
    assert texts(cv) == []


def test_a_hanging_tag_is_blank_and_drops_straight_from_its_string():
    cv = canvas()
    stick_airport.carry_on(cv, cv.comp, 480, stick_airport.FLOOR_FEET, tag=None, hanging=True)
    floor = stick_airport.FLOOR_FEET
    tag = [
        r for r in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("shape") if r.get("fill") == stick_airport.TAG
    ]
    assert [(float(r.get("x")), float(r.get("y")), float(r.get("width")), float(r.get("height"))) for r in tag] == [
        (522.0, floor - 396, 40.0, 86.0)
    ]
    with pytest.raises(StickDataError, match="hanging tag is blank"):
        stick_airport.carry_on(cv, cv.comp, 480, floor, tag="GROUP 4", hanging=True)


def test_the_scale_lights_one_weight_at_a_time_at_phone_size():
    cv = canvas()
    readings = ((0.0, "23.4"), (2.0, "22.9"))
    stick_airport.bag_scale(cv, cv.comp, 540, 1700, readings, 4.0)
    assert texts(cv) == ["23.4", "22.9"]
    assert stick_airport.READOUT_SIZE >= 110  # a phone's width of 1080 pixels is about 7 cm
    keyed = [k for k in xml(cv).iter() if k.tag.endswith("keyframe") or k.tag.endswith("key")]
    assert keyed, "each reading is lit only for its own time"


@pytest.mark.parametrize(
    "readings, end, match",
    [
        ((), 4.0, "at least one"),
        (((1.0, "23.4"),), 4.0, "start at 0"),
        (((0.0, "23.4"), (0.0, "23.3")), 4.0, "start at 0"),
        (((0.0, "23.4"), (5.0, "23.3")), 4.0, "start at 0"),
        (((0.0, "123.45"),), 4.0, "1 to 5"),
        (((0.0, "  "),), 4.0, "1 to 5"),
    ],
)
def test_the_scale_refuses_readings_it_cannot_show(readings, end, match):
    cv = canvas()
    with pytest.raises(StickDataError, match=match):
        stick_airport.bag_scale(cv, cv.comp, 540, 1700, readings, end)


def test_the_scale_needs_the_font():
    cv = canvas(None)
    with pytest.raises(Exception, match="readout"):
        stick_airport.bag_scale(cv, cv.comp, 540, 1700, ((0.0, "1"),), 4.0)


def test_the_ball_grows_with_what_it_wears():
    bare = canvas()
    stick_airport.coat_ball(bare, bare.comp, 400, 842, 170, layers=1)
    full = canvas()
    stick_airport.coat_ball(full, full.comp, 400, 842, 320, layers=4, hats=3, scarves=3, trousers=True, shoes=True)
    assert shapes(full) > shapes(bare) + 8


@pytest.mark.parametrize(
    "radius, kw, match",
    [
        (60, {}, "radius"),
        (200, {"layers": 0}, "coats"),
        (200, {"layers": 9}, "coats"),
        (200, {"hats": 9}, "hats"),
        (200, {"scarves": -1}, "scarves"),
    ],
)
def test_the_ball_refuses_what_it_cannot_wear(radius, kw, match):
    cv = canvas()
    with pytest.raises(StickDataError, match=match):
        stick_airport.coat_ball(cv, cv.comp, 400, 842, radius, **kw)


def test_the_palm_stands_and_refuses_a_stump():
    cv = canvas()
    stick_airport.palm(cv, cv.comp, 300, 1200)
    assert shapes(cv) >= 14
    with pytest.raises(StickDataError, match="at least 120"):
        stick_airport.palm(cv, cv.comp, 300, 1200, height=60)


def test_a_long_call_shrinks_to_stay_on_the_sign():
    assert stick_airport.now_size("GROUP 1") == stick_airport.now_size("FINAL CALL") == 72
    assert stick_airport.now_size("WELCOME 38°") < 54
