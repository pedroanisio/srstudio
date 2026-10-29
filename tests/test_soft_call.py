"""A call on the Soft meeting room's wall screen: the screen's frame, the opt-in slot, and the beach call graphic."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import WARM, Canvas, Signature, blob, registry, soft_props
from srstudio.soft_props import SoftPropError


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="10", duration=2, background=WARM.background)
    return scene, Canvas(scene, WARM, signature=Signature())


def elements(scene):
    return {el.get("id"): el for el in ET.fromstring(scene.to_bytes()).iter() if el.get("id")}


def test_the_screen_frame_maps_its_flat_corners_onto_the_wall_screen():
    (x, y), w, h, skew = blob.meeting_screen()
    _, a0, a1, u0, u1 = blob.WALL_DECOR["meeting-screen"]
    tilt = math.tan(math.radians(skew))
    assert (x, y) == pytest.approx(blob.room_point(a0 + 16, 0, u1 - 16))
    assert (x + w, y + w * tilt) == pytest.approx(blob.room_point(a1 - 16, 0, u1 - 16))  # the top edge, along the wall
    assert (x, y + h) == pytest.approx(blob.room_point(a0 + 16, 0, u0 + 16))  # the left edge, straight down


def test_the_meeting_room_draws_no_call_unless_given_one():
    scene, cv = canvas()
    blob.meeting_room(cv, cv.comp)
    assert not [i for i in elements(scene) if i.endswith("-screen-call")]


def test_a_call_on_the_screen_is_skewed_onto_the_wall_and_masked_to_it():
    scene, cv = canvas()
    seen = []
    blob.meeting_room(cv, cv.comp, on_screen=seen.append)
    found = elements(scene)
    call = found["soft-meeting-room-screen-call"]
    (x, y), w, h, skew = blob.meeting_screen()
    assert float(call.get("skewY")) == pytest.approx(skew) and float(call.get("x")) == pytest.approx(x)
    masks = [m for m in call.iter() if m.tag.rsplit("}", 1)[-1] == "mask"]
    assert (
        masks and float(masks[0].get("width")) == pytest.approx(w) and float(masks[0].get("height")) == pytest.approx(h)
    )
    assert seen and seen[0].id == "soft-meeting-room-screen-call"
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_the_beach_call_is_a_registered_soft_graphic_with_a_name_tag():
    entry = registry.get("graphic", "soft-beach-call")
    assert entry.style == "soft" and entry.summary
    scene, cv = canvas()
    _, w, h, _ = blob.meeting_screen()
    g = soft_props.beach_call(cv, cv.comp, w, h, name="BO · CEO")
    found = elements(scene)
    assert g.id == "beach-call" and {"beach-call-palm", "beach-call-sea", "beach-call-name"} <= set(found)
    errors = [f for f in scene.check() if f.severity == "error"]
    assert [f.code for f in errors] == ["xsd:idref"] and "caption-font" in errors[0].message  # the episode's font


@pytest.mark.parametrize("bad", [dict(w=0), dict(h=-5), dict(name=""), dict(name="X" * 30)])
def test_the_beach_call_refuses_an_empty_size_or_name(bad):
    _, cv = canvas()
    args = dict(w=300.0, h=200.0, name="BO") | bad
    with pytest.raises(SoftPropError):
        soft_props.beach_call(cv, cv.comp, args["w"], args["h"], name=args["name"])


def test_the_name_tag_can_move_inside_the_picture():
    scene, cv = canvas()
    soft_props.beach_call(cv, cv.comp, 300.0, 200.0, name="BO", tag=(60.0, 140.0))
    tag = elements(scene)["beach-call-tag"]
    assert (float(tag.get("x")), float(tag.get("y"))) == (60.0, 140.0)
    with pytest.raises(SoftPropError):
        soft_props.beach_call(cv, cv.comp, 300.0, 200.0, name="BO", tag=(290.0, 140.0), id="outside")
