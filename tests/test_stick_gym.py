"""The Stick gym: the front desk at dawn (its window keyed from night to sunrise) and the counter with its sign."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, registry, stick, stick_gym


def canvas(font: str | None = "inter") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset=font, namer=flat_counter("n"))


def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list[str]:
    return [t.get("text") for t in xml(cv).iter("text")]


def opacity_keys(root: ET.Element) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in root.iter("animate")
        if a.get("property") == "opacity"
    ]


def test_the_parts_are_registered_for_the_stick_style():
    for kind, name in (("location", "stick-gym"), ("prop", "stick-gym-counter")):
        assert registry.get(kind, name).style == "stick"


def test_the_gym_draws_its_brand_its_window_and_the_signature():
    cv = canvas()
    stick_gym.gym(cv, cv.comp, 5.0)
    assert stick_gym.BRAND.upper() in texts(cv) and "NO EXCUSES" in texts(cv)
    root = xml(cv)
    assert len(list(root.iter("shape"))) > 30  # the skyline, the rack, the treadmill, the floor mats
    assert opacity_keys(root) == []  # no sunrise: the night holds still
    with pytest.raises(ValueError, match="font"):
        stick_gym.gym(canvas(None), None, 5.0)


def test_the_sun_rises_in_the_window_from_its_second():
    cv = canvas()
    stick_gym.gym(cv, cv.comp, 5.0, sunrise=2.0)
    keys = opacity_keys(xml(cv))
    assert [(2.0, 0.0), (2.0 + stick_gym.DAWN, 1.0)] in [k[-2:] for k in keys]
    assert any(k[0] == (0.0, 0.0) for k in keys)  # dark until then
    day = canvas()
    stick_gym.gym(day, day.comp, 5.0, sunrise=0.0)  # already up: drawn, never keyed
    assert opacity_keys(xml(day)) == []
    for bad in (-1.0, 5.0, float("nan")):
        with pytest.raises(stick.StickDataError, match="sunrise"):
            stick_gym.gym(canvas(), None, 5.0, sunrise=bad)


def test_the_counter_carries_its_sign_and_fine_print():
    cv = canvas()
    stick_gym.counter(cv, cv.comp, sign="CANCEL ANYTIME*", fine="*in person")
    assert {"CANCEL ANYTIME*", "*in person"} <= set(texts(cv))
    plain = canvas()
    stick_gym.counter(plain, plain.comp, sign="WELCOME")
    assert texts(plain) == ["WELCOME"]
    for sign, fine, match in (("", "", "sign"), ("X" * (stick_gym.SIGN_CHARS + 1), "", "sign"),
                              ("OK", "x" * (stick_gym.FINE_CHARS + 1), "fine print")):  # fmt: skip
        with pytest.raises(stick.StickDataError, match=match):
            stick_gym.counter(canvas(), None, sign=sign, fine=fine)


def test_the_staff_stands_behind_the_counter_and_the_member_in_front():
    member_x = stick.STANDING["stand"].head[0] + stick_gym.MEMBER_AT[0]
    staff_x = stick_gym.STAFF_AT[0] - stick.STANDING["stand"].head[0]
    left, right = stick_gym.COUNTER_X
    assert member_x < left < staff_x < right
    x, y = stick_gym.SIGN_CENTRE
    assert left < x < right and y < stick_gym.COUNTER_TOP
