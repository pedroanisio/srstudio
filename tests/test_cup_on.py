"""A cup stands on a surface: the reel says where the surface is, and the drawing says where the cup's base is."""

import math
import re
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, props


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=5)
    return Canvas(scene)


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _cup(cv):
    """The cup's group as the scene will draw it."""
    root = ET.fromstring(cv.scene.to_bytes())
    return next(e for e in root.iter() if _local(e.tag) == "group" and e.get("id", "").startswith("coffee-cup"))


@pytest.mark.parametrize("scale", [0.5, 1, 1.4])
@pytest.mark.parametrize("top", [0, 236, -40.5])
def test_the_base_of_the_cup_is_on_the_surface_at_any_size(top, scale):
    cv = canvas()
    props.cup_on(cv, cv.comp, 10, top, scale)
    cup = _cup(cv)
    assert float(cup.get("y")) + props.CUP_BASE * scale == pytest.approx(top)
    assert float(cup.get("x")) == 10
    assert float(cup.get("scaleX")) == float(cup.get("scaleY")) == scale


def test_the_base_the_helper_seats_is_the_base_the_cup_draws():
    cv = canvas()
    props.coffee_cup(cv, cv.comp, 0, 0)
    paths = [e.get("path") or "" for e in _cup(cv).iter()]
    body = next(d for d in paths if d.startswith("M-28 -18"))
    assert max(float(y) for y in re.findall(r"L-?\d+ (-?\d+)", body)) == props.CUP_BASE


def test_the_contact_shadow_stays_and_a_cup_can_drop_it():
    shaded, plain = canvas(), canvas()
    props.cup_on(shaded, shaded.comp, 0, 100)
    props.cup_on(plain, plain.comp, 0, 100, shadow=False)
    assert len(list(_cup(shaded).iter())) > len(list(_cup(plain).iter()))


@pytest.mark.parametrize("scale", [0, -1, True, math.nan, math.inf, "0.5", None])
def test_a_size_no_cup_can_stand_at_is_refused_before_anything_is_drawn(scale):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(props.PropError) as caught:
        props.cup_on(cv, cv.comp, 0, 100, scale)
    assert caught.value.to_dict()["path"] == "scale"
    assert caught.value.to_dict()["remedy"]
    assert cv.scene.to_bytes() == before
    assert cv._serial == 0


@pytest.mark.parametrize("top", [True, math.nan, math.inf, "50%", None])
def test_a_surface_that_is_not_a_height_is_refused_before_anything_is_drawn(top):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(props.PropError) as caught:
        props.cup_on(cv, cv.comp, 0, top)
    assert caught.value.to_dict()["path"] == "top"
    assert cv.scene.to_bytes() == before
    assert cv._serial == 0
