"""The Cutout tip tablet: a counter-top payment screen asking for a tip, whose buttons light up when tapped."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import CAFE, Canvas, flat_counter, props, registry


def canvas(font: str | None = "font") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=4, background=CAFE.background)
    return Canvas(scene, CAFE, font_asset=font, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def test_the_tablet_is_a_registered_cutout_prop():
    entry = registry.get("prop", "tip-tablet")
    assert entry.style == "cutout" and entry.summary


def test_it_letters_the_heading_the_options_and_a_tiny_no_tip():
    cv = canvas()
    props.tip_tablet(cv, cv.comp, 560, 1240, heading="Add a tip", options=("20%", "25%", "30%"))
    texts = {t.get("text"): float(t.get("size")) for t in xml(cv).iter("text")}
    assert {"Add a tip", "20%", "25%", "30%", "no tip"} <= set(texts)
    assert texts["no tip"] < texts["20%"] / 2  # the way out is the smallest thing on the screen


def test_each_pick_lights_its_button_until_the_next():
    cv = canvas()
    props.tip_tablet(cv, cv.comp, 560, 1240, picks=((1.0, 1), (2.0, 2)))
    gates = [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in xml(cv).iter("animate")
        if a.get("property") == "opacity"
    ]
    assert [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)] in gates
    assert [(0.0, 0.0), (2.0, 1.0)] in gates


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(heading=" "), "heading"),
        (dict(options=()), "options"),
        (dict(options=("a", "b", "c", "d", "e")), "options"),
        (dict(options=("10%", "")), "options"),
        (dict(picks=((1.0, 3),)), "pick"),
        (dict(picks=((2.0, 0), (1.0, 1))), "pick"),
        (dict(picks=((-1.0, 0),)), "pick"),
        (dict(scale=0), "scale"),
    ],
)
def test_it_refuses_a_screen_it_cannot_show(kw, match):
    with pytest.raises(ValueError, match=match):
        props.tip_tablet(canvas(), None, 0, 0, **kw)


def test_it_needs_a_font():
    with pytest.raises(ValueError, match="font"):
        props.tip_tablet(canvas(None), None, 0, 0)
