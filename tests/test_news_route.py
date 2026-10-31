"""A route on Gus's phone: a map that does a joke's work, and an anchor who cries, both refused when they are wrong."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, news_inked, news_kit, parts
from srstudio.news_inked import Pin, route_insert
from srstudio.news_kit import NewsKitError, Pose

PATH = ((110.0, 600.0), (300.0, 500.0), (560.0, 130.0))
HOME = Pin(560.0, 130.0, "HOME", news_kit.MINT)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")


def measure(text: str, size: float) -> float:
    return 0.42 * size * len(text)


def drawn(**kw) -> dict[str, ET.Element]:
    cv = canvas()
    args = dict(title="Maps", track=PATH, pins=(HOME,), start=2.0, end=6.0, measure=measure)
    route_insert(cv, cv.comp, **{**args, **kw})
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return {node.get("id", ""): node for node in root.iter()}


def test_the_route_is_a_registered_proposed_graphic():
    record = parts.get("news-route").versions[-1]
    assert (record.number, record.status, record.approval) == (1, "proposed", None)


def test_the_phone_is_up_only_from_start_to_end():
    node = drawn()["news-route"]
    assert (float(node.get("start", "0")), float(node.get("end", "0"))) == (2.0, 6.0)


def test_the_route_draws_itself_one_leg_after_another():
    groups = drawn()
    assert float(groups["news-route-leg-0"].get("start", "0")) == 2.0
    assert float(groups["news-route-leg-1"].get("start", "0")) > 2.0
    assert float(groups["news-route-leg-1"].get("end", "0")) == 6.0


def test_the_marker_finishes_the_route_inside_the_draw_time():
    marker = drawn(draw=1.5)["news-route-marker"]
    times = [float(k.get("time", "0")) for k in marker.iter() if k.tag.endswith("key")]
    assert max(times) == pytest.approx(3.5)


def test_a_straight_line_is_only_there_when_asked_for():
    assert "news-route-direct" not in drawn()
    assert "news-route-direct" in drawn(direct=(PATH[0], PATH[-1]))


def test_a_pin_says_what_it_marks():
    cv = canvas()
    route_insert(cv, cv.comp, "Maps", PATH, (HOME, Pin(300.0, 500.0, "GUS", news_kit.TANGERINE)), 2.0, 6.0, measure)
    words = ET.tostring(ET.fromstring(cv.scene.to_bytes(layout="pretty")), encoding="unicode")
    assert "HOME" in words and "GUS" in words


@pytest.mark.parametrize(
    "bad",
    [
        dict(track=()),
        dict(track=(PATH[0],)),
        dict(track=((-5.0, 100.0), (300.0, 300.0))),
        dict(track=((100.0, 100.0), (900.0, 300.0))),
        dict(track=((100.0, 100.0), (300.0, 2000.0))),
        dict(pins=(Pin(900.0, 100.0, "HOME", news_kit.MINT),)),
        dict(start=6.0, end=2.0),
        dict(draw=0.0),
        dict(draw=5.0),
        dict(marker="anvil"),
    ],
)
def test_a_route_that_cannot_be_drawn_stops_the_build(bad):
    with pytest.raises(NewsKitError):
        drawn(**bad)


@pytest.mark.parametrize("copy", ["Follow for more", "Comment below"])
def test_bait_on_a_pin_stops_the_build(copy):
    with pytest.raises(NewsKitError):
        drawn(pins=(Pin(300.0, 300.0, copy, news_kit.MINT),))


@pytest.mark.parametrize("copy", ["Follow for more", "Comment below"])
def test_bait_in_the_title_stops_the_build(copy):
    with pytest.raises(NewsKitError):
        drawn(title=copy)


def test_a_pin_label_too_wide_for_the_screen_stops_the_build():
    with pytest.raises(NewsKitError):
        drawn(pins=(Pin(300.0, 300.0, "A VERY LONG LABEL " * 8, news_kit.MINT),))


def test_gus_can_cry_and_the_shut_eye_stays_what_it_was():
    assert Pose(eyes="weep").eyes == "weep"
    wet, dry = canvas(), canvas()
    news_inked.gus(wet, wet.comp, Pose("weep", "frown"))
    news_inked.gus(dry, dry.comp, Pose("shut", "frown"))
    assert len(list(ET.fromstring(wet.scene.to_bytes()).iter())) > len(list(ET.fromstring(dry.scene.to_bytes()).iter()))


def test_the_first_version_cries_with_its_eyes_shut():
    cv = canvas()
    news_kit.gus(cv, cv.comp, Pose("weep", "frown"))
