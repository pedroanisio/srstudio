"""The family car trip: the mirror that fills the frame, the swim ring, the blinker and the sun hat, each refusing what
it cannot draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_roadtrip
from srstudio.canvas import Signature
from srstudio.stick import StickDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature())


def xml(cv: Canvas) -> bytes:
    return cv.scene.to_bytes(layout="pretty")


def test_the_mirror_masks_what_is_drawn_into_it():
    cv = canvas()
    seen = []
    glass = stick_roadtrip.rear_view(cv, cv.comp, seen.append)
    assert seen == [glass]
    masks = [m for m in ET.fromstring(xml(cv)).iter("mask") if m.get("type") == "path"]
    assert len(masks) == 1


def test_a_mirror_is_drawn_the_same_every_time():
    """A reel cuts from its last mirror back to its first: nothing in it may depend on the hour."""
    assert xml(_mirrored()) == xml(_mirrored())


def _mirrored() -> Canvas:
    cv = canvas()
    stick_roadtrip.rear_view(cv, cv.comp)
    return cv


def test_a_figure_that_cannot_draw_is_refused():
    cv = canvas()
    with pytest.raises(StickDataError, match="function"):
        stick_roadtrip.rear_view(cv, cv.comp, "Dad")


@pytest.mark.parametrize(
    "kw", [{"rx": 10.0}, {"ry": 20.0}, {"rx": float("nan")}, {"rx": 400.0, "ry": 100.0}, {"band": "red"}]
)
def test_a_ring_refuses_what_it_cannot_draw(kw):
    cv = canvas()
    with pytest.raises(StickDataError, match="ring"):
        stick_roadtrip.swim_ring(cv, cv.comp, 100, 100, **kw)


def test_a_squashed_ring_keeps_its_tube():
    cv = canvas()
    stick_roadtrip.swim_ring(cv, cv.comp, 100, 200, rx=150, ry=90)
    drawn = xml(cv)
    assert b"#d9483b" in drawn and b"A 150 90" in drawn


def lit_spans(cv: Canvas) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in ET.fromstring(xml(cv)).iter("animate")
        if a.get("property") == "opacity"
    ]


def test_the_blinker_shows_lit_only_after_each_click():
    cv = canvas()
    stick_roadtrip.blinker(cv, cv.comp, 540, 1400, 3.0, (0.5, 1.5))
    hide = stick_roadtrip.CLICK_SHOWS
    assert lit_spans(cv) == [[(0.0, 0.0), (0.5, 1.0), (0.5 + hide, 0.0), (1.5, 1.0), (1.5 + hide, 0.0)]]


def test_a_blinker_with_no_clicks_stays_dark():
    cv = canvas()
    stick_roadtrip.blinker(cv, cv.comp, 540, 1400, 3.0, ())
    assert lit_spans(cv) == [[(0.0, 0.0)]]


def test_a_click_at_the_end_of_a_shot_is_cut_with_it():
    cv = canvas()
    stick_roadtrip.blinker(cv, cv.comp, 540, 1400, 1.0, (0.9,))
    assert lit_spans(cv) == [[(0.0, 0.0), (0.9, 1.0), (1.0, 0.0)]]


@pytest.mark.parametrize(
    "args, kw",
    [
        ((540, 1400, 0.0, ()), {}),
        ((540, 1400, 3.0, (2.0, 1.0)), {}),
        ((540, 1400, 3.0, (3.5,)), {}),
        ((540, 1400, 3.0, (-1.0,)), {}),
        ((float("inf"), 1400, 3.0, ()), {}),
        ((540, 1400, 3.0, ()), {"scale": 0}),
    ],
)
def test_a_blinker_refuses_what_it_cannot_draw(args, kw):
    cv = canvas()
    with pytest.raises(StickDataError):
        stick_roadtrip.blinker(cv, cv.comp, *args, **kw)


def test_a_sunhat_is_a_look_the_rig_draws():
    bare, hatted = canvas(), canvas()
    pose = stick.RigKey(0, next(iter(stick.SEATED)), stick.Face())
    stick.rig(bare, bare.comp, [pose], 2.0)
    stick.rig(hatted, hatted.comp, [pose], 2.0, look=stick.Look(sunhat="#e8cf8e"))
    assert b"#e8cf8e" not in xml(bare)
    assert b"#e8cf8e" in xml(hatted)


def test_a_sunhat_of_no_colour_is_refused():
    with pytest.raises(StickDataError, match="sunhat"):
        stick.check_look(stick.Look(sunhat="straw"))


@pytest.mark.parametrize("name", ["stick-rear-view", "stick-swim-ring", "stick-blinker"])
def test_the_parts_are_registered(name):
    assert registry.get("prop", name)
