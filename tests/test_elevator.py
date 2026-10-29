"""The Cutout elevator: standing legs for the office actors, the cab with its doors and floor display, its slots."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, Signature, cast, locations, registry
from srstudio.rig import Performance


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def canvas(signed: bool = True):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12, background=OFFICE.background)
    return scene, Canvas(scene, OFFICE, signature=Signature() if signed else None)


def root(scene) -> ET.Element:
    return ET.fromstring(scene.to_bytes())


def ids(scene) -> list[str]:
    return [el.get("id") for el in root(scene).iter() if el.get("id")]


def by_id(scene, name):
    return next(el for el in root(scene).iter() if el.get("id") == name)


def keys(el, prop: str) -> list[tuple[float, float]]:
    return [
        (float(k.get("time")), float(k.get("value")))
        for a in el.iter()
        if local(a.tag) == "animate" and a.get("property") == prop
        for k in a
        if local(k.tag) == "key"
    ]


def test_a_standing_office_actor_has_legs_down_to_the_floor_behind_its_torso():
    scene, cv = canvas()
    boss = cast.Manager(cv, tag="manager-lift")
    boss.build(cv.comp, 760, 900, 1.2, Performance(extras={"legs": "standing"}))
    order = ids(scene)
    legs = f"{boss.tag_base}-legs"
    assert legs in order and order.index(legs) < order.index(f"{boss.tag_base}-head")
    assert cast.OfficeActor.STANDING_LEGS > 300  # trouser legs and shoes below the torso's bottom
    assert [f for f in scene.check() if f.severity == "error"] == []


def test_standing_feet_land_on_the_cab_floor():
    for bottom in (cast.Manager.bottom, cast.Candidate.bottom):
        y = locations.elevator_stand_y(bottom, 1.25)
        assert y + (bottom + cast.OfficeActor.STANDING_LEGS) * 1.25 == pytest.approx(locations.ELEVATOR_FLOOR)


def test_the_elevator_is_a_registered_cutout_location_gated_lit_and_signed():
    entry = registry.get("location", "elevator")
    assert entry.style == "cutout" and entry.summary
    scene, cv = canvas()
    g = locations.elevator(cv, cv.comp, shots=[(0.5, 4)])
    names = set(ids(scene))
    assert g.id == "location-elevator"
    assert {"location-elevator-light", "location-elevator-doors", "sig-cactus", "sig-code"} <= names
    assert [f for f in scene.check() if f.severity == "error"] == []
    scene, cv = canvas(signed=False)
    locations.elevator(cv, cv.comp)
    assert not [i for i in ids(scene) if i.startswith("sig-")]


def test_the_floor_display_shows_each_floor_in_its_span():
    scene, cv = canvas()
    locations.elevator(cv, cv.comp, floors=((0.0, 1), (1.0, 2), (2.5, 4)))
    assert {f"location-elevator-floor-{n}" for n in (1, 2, 4)} <= set(ids(scene))  # seven-segment digits, no font
    segments = [el for el in by_id(scene, "location-elevator-floor-4").iter() if local(el.tag) == "shape"]
    assert len(segments) == len(locations.SEGMENTS["4"])
    shown = keys(by_id(scene, "location-elevator-floor-2"), "opacity")
    assert shown[:3] == [(0.0, 0.0), (1.0, 1.0), (2.5, 0.0)]


def test_the_doors_slide_open_and_shut_in_their_spans():
    scene, cv = canvas()
    locations.elevator(cv, cv.comp, doors=((2.0, 5.0),))
    left = keys(by_id(scene, "location-elevator-door-left"), "x")
    assert left[0] == (0.0, 0.0) and (2.0, 0.0) in left and (5.0 + locations.DOOR_SLIDE, 0.0) in left
    assert min(v for _, v in left) == pytest.approx(-locations.DOOR_W)  # fully open: slid behind the wall


def test_the_slots_draw_the_riders_over_the_doors_and_the_floor_in_front():
    scene, cv = canvas()
    locations.elevator(cv, cv.comp, riders=lambda g: cv.group(g, "riders"), on_floor=lambda g: cv.group(g, "front"))
    order = ids(scene)
    assert order.index("location-elevator-doors") < order.index("riders") < order.index("front")


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(floors=()), "floor"),
        (dict(floors=((0.5, 1),)), "floor"),
        (dict(floors=((0.0, 1), (0.0, 2))), "floor"),
        (dict(floors=((0.0, 0),)), "floor"),
        (dict(floors=((0.0, 100),)), "floor"),
        (dict(doors=((3.0, 2.0),)), "doors"),
        (dict(doors=((1.0, 3.0), (2.0, 4.0))), "doors"),
        (dict(lit=100), "lit"),
    ],
)
def test_the_elevator_refuses_floors_and_doors_it_cannot_show(kw, match):
    _, cv = canvas()
    with pytest.raises(ValueError, match=match):
        locations.elevator(cv, cv.comp, **kw)


def test_the_arrow_points_down_when_the_cab_is_going_down_and_up_by_default():
    up, cv_up = canvas()
    locations.elevator(cv_up, cv_up.comp)
    same, cv_same = canvas()
    locations.elevator(cv_same, cv_same.comp, going="up")
    assert up.to_bytes(layout="pretty") == same.to_bytes(layout="pretty")
    down, cv_down = canvas()
    locations.elevator(cv_down, cv_down.comp, going="down")
    assert b"M490 440 L506 470 L522 440Z" in down.to_bytes(layout="pretty")
    assert b"M490 470 L506 440 L522 470Z" not in down.to_bytes(layout="pretty")
    with pytest.raises(ValueError, match="going"):
        locations.elevator(cv_down, cv_down.comp, going="sideways")
