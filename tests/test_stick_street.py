"""The Stick road home: the sets and inserts draw, carry the signature, and refuse what they cannot draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick_street
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas(*, signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    mark = Signature() if signed else None
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=mark)


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


@pytest.mark.parametrize("draw", [stick_street.street, stick_street.road_plan, stick_street.road_ahead])
def test_each_location_carries_both_signature_marks(draw):
    cv = canvas(signed=True)
    draw(cv, cv.comp)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_a_scar_is_drawn_for_each_turn_before():
    plain, scarred = canvas(), canvas()
    stick_street.road_plan(plain, plain.comp, scars=0)
    stick_street.road_plan(scarred, scarred.comp, scars=2)
    assert len(list(xml(scarred).iter("shape"))) == len(list(xml(plain).iter("shape"))) + 2


@pytest.mark.parametrize("scars", [-1, 9, 1.5])
def test_the_road_refuses_a_bad_number_of_scars(scars):
    with pytest.raises(StickDataError, match="skid"):
        stick_street.road_plan(canvas(), None, scars=scars)


def test_the_tree_grows_and_refuses_nothing():
    with pytest.raises(StickDataError, match="tree"):
        stick_street.street(canvas(), None, tree=0.0)


def test_the_window_is_a_mask():
    cv = canvas()
    stick_street.in_window(cv, cv.comp)
    assert list(xml(cv).iter("mask"))


def test_a_sign_needs_words_and_time():
    with pytest.raises(StickDataError, match="words"):
        stick_street.road_sign(canvas(), None, 2.0, text=" ")
    with pytest.raises(StickDataError, match="seconds"):
        stick_street.road_sign(canvas(), None, 0.0, text="AIRPORT 2")


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv: stick_street.side_car(cv, cv.comp),
        lambda cv: stick_street.top_car(cv, cv.comp),
        lambda cv: stick_street.suitcases(cv, cv.comp, 540, 980),
        lambda cv: stick_street.stove_knob(cv, cv.comp),
        lambda cv: stick_street.door_lock(cv, cv.comp),
        lambda cv: stick_street.road_sign(cv, cv.comp, 2.0, text="AIRPORT 2"),
        lambda cv: stick_street.window_frame(cv, cv.comp),
    ],
)
def test_each_prop_draws(draw):
    cv = canvas()
    draw(cv)
    assert list(xml(cv).iter("shape")) or list(xml(cv).iter("group"))
