"""The Stick kitchen: the set and its props draw, carry the signature, and refuse what they cannot draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick_home
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas(*, font: str | None = "inter", signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset=font, namer=flat_counter("n"), signature=Signature() if signed else None)


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


def test_the_kitchen_carries_both_signature_marks():
    cv = canvas(signed=True)
    stick_home.kitchen(cv, cv.comp)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


@pytest.mark.parametrize("draw", [stick_home.table, stick_home.fridge_open, stick_home.safe_open])
def test_the_furniture_draws(draw):
    cv = canvas()
    draw(cv, cv.comp)
    assert list(xml(cv).iter("shape"))


def test_every_pose_keeps_the_hands_on_the_frame():
    for pose in stick_home.POSES.values():
        for x, y in pose.hands:
            assert 0 <= x <= 1080 and 0 <= y <= 1920


def test_the_near_hand_of_the_offer_reaches_past_the_centre_of_the_table():
    assert stick_home.LEFT_AT[0] + stick_home.POSES["offer"].hands[1][0] > 540


def test_the_plan_carries_both_signature_marks():
    cv = canvas(signed=True)
    stick_home.plan(cv, cv.comp)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_a_figure_from_above_steps_its_feet_in_turn():
    cv = canvas()
    stick_home.from_above(cv, cv.comp, 2.0, hair="bun", phone="#e8558f", rate=6.0)
    assert len(list(xml(cv).iter("shape"))) >= 8


@pytest.mark.parametrize("kw", [dict(hair="mohawk"), dict(hair="bun", end=0.0)])
def test_a_figure_from_above_refuses_what_it_cannot_draw(kw):
    cv = canvas()
    kw = {"end": 2.0, **kw}
    with pytest.raises(StickDataError):
        stick_home.from_above(cv, cv.comp, kw.pop("end"), **kw)


@pytest.mark.parametrize("draw", [stick_home.handset, stick_home.key])
def test_a_bad_scale_is_refused(draw):
    cv = canvas()
    with pytest.raises(StickDataError, match="scale"):
        draw(cv, cv.comp, 1, 1, scale=0.0)


def test_the_chat_needs_all_three_lines():
    cv = canvas()
    with pytest.raises(StickDataError, match="chat"):
        stick_home.reply(cv, cv.comp, name="Him", sent="", answer="who is this")
    stick_home.reply(cv, cv.comp, name="Him", sent="hi", answer="who is this")
    assert list(xml(cv).iter("text")) or list(xml(cv).iter("textLayer")) or list(xml(cv).iter("layer"))


def test_a_reel_can_place_the_kitchens_marks_itself():
    with_marks, without = canvas(signed=True), canvas(signed=True)
    stick_home.kitchen(with_marks, with_marks.comp)
    stick_home.kitchen(without, without.comp, marks=False)
    marks = [
        [g.get("id") for g in xml(cv).iter("group") if (g.get("id") or "").startswith("sig-")]
        for cv in (with_marks, without)
    ]
    assert len(marks[0]) == 2 and marks[1] == []
