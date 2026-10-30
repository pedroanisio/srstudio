"""The Stick coffee corner: the set and what it leaves on people draw, carry the signature, and refuse nonsense."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick_office
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas(*, signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(
        scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature() if signed else None
    )


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


def test_the_corner_carries_both_signature_marks():
    cv = canvas(signed=True)
    stick_office.corner(cv, cv.comp)
    ids = [g.get("id") or "" for g in xml(cv).iter("group")]
    assert sum(i.startswith("sig-cactus") for i in ids) == 1 and sum(i.startswith("sig-code") for i in ids) == 1


def test_on_figure_mirrors_with_the_rig():
    pose = stick_office.POSES["mug"]
    plain = stick_office.on_figure(pose, at=(100.0, 0.0))
    mirrored = stick_office.on_figure(pose, at=(1000.0, 0.0), flip=True)
    assert plain["hand"] == (100.0 + pose.hands[1][0], pose.hands[1][1])
    assert mirrored["hand"] == (1000.0 - pose.hands[1][0], pose.hands[1][1])
    assert plain["neck"][1] == mirrored["neck"][1]


def test_the_view_is_held_to_the_window():
    cv = canvas()
    stick_office.view(cv, cv.comp)
    assert list(xml(cv).iter("mask"))


def test_the_meteor_lands_inside_its_shot():
    cv = canvas()
    stick_office.meteor(cv, cv.comp, 2.0, land=1.0)
    assert list(xml(cv).iter("shape"))
    with pytest.raises(StickDataError, match="lands"):
        stick_office.meteor(canvas(), None, 2.0, land=3.0)


def test_a_parrot_faces_one_way_or_the_other():
    with pytest.raises(StickDataError, match="parrot"):
        stick_office.parrot(canvas(), None, 1, 1, facing=0)


def test_flames_need_time_and_a_stone_needs_words():
    with pytest.raises(StickDataError, match="flames"):
        stick_office.flames(canvas(), None, 1, 1, 0.0)
    with pytest.raises(StickDataError, match="words"):
        stick_office.tombstone(canvas(), None, 300.0, words=" ")


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv: stick_office.counter(cv, cv.comp),
        lambda cv: stick_office.mug(cv, cv.comp, 500, 900),
        lambda cv: stick_office.cast(cv, cv.comp, (400, 900), (500, 1000)),
        lambda cv: stick_office.brace(cv, cv.comp, 540, 857),
        lambda cv: stick_office.parrot(cv, cv.comp, 600, 860),
        lambda cv: stick_office.flames(cv, cv.comp, 540, 660, 2.0),
        lambda cv: stick_office.tombstone(cv, cv.comp, 320.0, words="GOOD."),
    ],
)
def test_each_prop_draws(draw):
    cv = canvas()
    draw(cv)
    assert list(xml(cv).iter("shape")) or list(xml(cv).iter("group"))
