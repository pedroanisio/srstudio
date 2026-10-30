"""The Cutout far plane: an opt-in blur on the room behind the cast (``depth=``), with the cast, the props and the
signature marks left sharp; without it each set keeps its shipped bytes."""

import hashlib
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, Signature, locations
from support.signature import TODAY, _canvas


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def blurred(cv) -> list[ET.Element]:
    root = ET.fromstring(cv.scene.to_bytes())
    blurs = {e.get("id") for e in root.iter() if local(e.tag) == "effect" and e.get("type") == "blur"}
    return [g for g in root.iter() if local(g.tag) == "group" and set((g.get("effects") or "").split()) & blurs]


def ids_under(nodes) -> set[str]:
    return {el.get("id") for n in nodes for el in n.iter() if el.get("id")}


def elevator_canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=6, background=OFFICE.background)
    return Canvas(scene, OFFICE, signature=Signature())


BUILDERS = {
    "office_wide": lambda cv, **kw: locations.office_wide(cv, cv.comp, at_desk=lambda g: cv.group(g, "cast"), **kw),
    "office_reverse": lambda cv, **kw: locations.office_reverse(
        cv, cv.comp, in_chair=lambda g: cv.group(g, "cast"), **kw
    ),  # fmt: skip
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_without_depth_the_office_keeps_its_bytes(name):
    draw = getattr(locations, name)
    for kw in ({}, dict(depth=None)):
        cv = _canvas()
        draw(cv, cv.comp, **kw)
        assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == TODAY[name]


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_depth_blurs_the_room_and_leaves_the_cast_and_the_marks_sharp(name):
    cv = _canvas()
    BUILDERS[name](cv, depth=3.0)
    far = blurred(cv)
    assert len(far) == 1
    inside = ids_under(far)
    assert "cast" not in inside
    assert not {i for i in inside if i.startswith("sig-")}  # the signature never sits under a blur
    assert [f for f in cv.scene.check() if f.severity == "error"] == []


def test_the_elevator_blurs_the_hallway_but_not_its_cactus_or_the_riders():
    plain, deep = elevator_canvas(), elevator_canvas()
    locations.elevator(plain, plain.comp, riders=lambda g: plain.group(g, "cast"))
    locations.elevator(deep, deep.comp, riders=lambda g: deep.group(g, "cast"), depth=2.5)
    assert blurred(plain) == []
    far = blurred(deep)
    assert len(far) == 1
    inside = ids_under(far)
    assert "cast" not in inside and not {i for i in inside if i.startswith("sig-")}
    assert [f for f in deep.scene.check() if f.severity == "error"] == []


def test_the_elevator_without_depth_draws_the_same_bytes_as_before():
    a, b = elevator_canvas(), elevator_canvas()
    locations.elevator(a, a.comp)
    locations.elevator(b, b.comp, depth=None)
    assert a.scene.to_bytes() == b.scene.to_bytes()


@pytest.mark.parametrize("bad", [0, -1.0, True, "3", float("nan")])
def test_a_depth_that_is_not_a_positive_radius_is_refused(bad):
    with pytest.raises(locations.LocationError, match="depth"):
        BUILDERS["office_reverse"](_canvas(), depth=bad)
    with pytest.raises(locations.LocationError, match="depth"):
        locations.elevator(elevator_canvas(), None, depth=bad)


def test_an_instanced_office_cannot_blur_a_shared_room():
    with pytest.raises(locations.LocationError, match="depth"):
        locations.office_wide(_canvas(), None, instanced=True, depth=2.0)
