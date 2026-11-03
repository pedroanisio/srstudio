"""The Stick kitchen: the set and its props draw, carry the signature, and refuse what they cannot draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_home
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


def test_the_bedroom_carries_both_signature_marks():
    cv = canvas(signed=True)
    stick_home.bedroom(cv, cv.comp)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_the_alarm_flashes_only_when_asked_and_refuses_what_it_cannot_draw():
    quiet = canvas()
    stick_home.smoke_alarm(quiet, quiet.comp, 540, 960)
    loud = canvas()
    stick_home.smoke_alarm(loud, loud.comp, 540, 960, flashes=(1.0, 2.0))
    assert len(list(xml(loud).iter("shape"))) == len(list(xml(quiet).iter("shape"))) + 1
    with pytest.raises(StickDataError, match="scale"):
        stick_home.smoke_alarm(quiet, quiet.comp, 540, 960, scale=0)
    with pytest.raises(StickDataError, match="flash"):
        stick_home.smoke_alarm(quiet, quiet.comp, 540, 960, flashes=(-1.0,))


def test_the_mound_letters_a_small_stone_and_refuses_a_long_one():
    cv = canvas()
    stick_home.mound(cv, cv.comp, 540, 1500, words="ALL 5")
    assert "ALL 5" in [t.get("text") for t in xml(cv).iter("text")]
    with pytest.raises(StickDataError, match="small stone"):
        stick_home.mound(cv, cv.comp, 540, 1500, words="IN LOVING MEMORY")


@pytest.mark.parametrize("draw", [stick_home.chair, stick_home.shovel])
def test_the_chair_and_the_shovel_draw(draw):
    cv = canvas()
    draw(cv, cv.comp, 540, 1500)
    assert list(xml(cv).iter("shape"))


def test_a_message_reads_at_phone_size_and_refuses_what_would_not():
    cv = canvas()
    stick_home.message(cv, cv.comp, sender="MOM", text="We need to talk.")
    words = [t.get("text") for t in xml(cv).iter("text")]
    assert "MOM" in words and "We need to talk." in words
    assert stick_home.MESSAGE_SIZE >= 96  # 96 px of 1920 stays over 3 mm tall on a 15 cm phone
    with pytest.raises(StickDataError, match="at most 48"):
        stick_home.message(cv, cv.comp, sender="MOM", text="x" * (stick_home.MESSAGE_CHARS + 1))
    with pytest.raises(StickDataError, match="sender and a text"):
        stick_home.message(cv, cv.comp, sender=" ", text="hi")
    with pytest.raises(StickDataError, match="sender and a text"):
        stick_home.message(cv, cv.comp, sender="MOM", text=" ")


def test_a_message_needs_the_font():
    cv = canvas(font=None)
    with pytest.raises(Exception, match="message"):
        stick_home.message(cv, cv.comp, sender="MOM", text="hi")


def test_a_reel_can_place_the_kitchens_marks_itself():
    with_marks, without = canvas(signed=True), canvas(signed=True)
    stick_home.kitchen(with_marks, with_marks.comp)
    stick_home.kitchen(without, without.comp, marks=False)
    marks = [
        [g.get("id") for g in xml(cv).iter("group") if (g.get("id") or "").startswith("sig-")]
        for cv in (with_marks, without)
    ]
    assert len(marks[0]) == 2 and marks[1] == []


def test_the_study_leaves_its_marks_to_the_reel_when_asked():
    """A reel that throws the room out of focus draws the marks itself, or the blur softens them (ADR 0001)."""

    with_marks, without = canvas(signed=True), canvas(signed=True)
    stick.room(with_marks, with_marks.comp)
    stick.room(without, without.comp, marks=False)
    assert b"sig-cactus" in with_marks.scene.to_bytes() and b"sig-code" in with_marks.scene.to_bytes()
    assert b"sig-cactus" not in without.scene.to_bytes() and b"sig-code" not in without.scene.to_bytes()
