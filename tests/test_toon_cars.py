"""The car parts: an inside with a road going past, what goes past it, and a pad that keeps count. Each refuses what it
cannot draw, and nothing is drawn before its time."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, specimens, toon_cars, toon_house, toon_world
from srstudio.toon import ToonDataError
from srstudio.toon_cars import Passing


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas, prefix: str) -> list[ET.Element]:
    return [n for n in tree(cv).iter("group") if n.get("id", "").startswith(prefix)]


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("location", "toon-car-inside", toon_cars.car_inside),
        ("prop", "toon-car-seat", toon_cars.seat),
        ("prop", "toon-side-car", toon_cars.side_car),
        ("prop", "toon-school-bus", toon_cars.school_bus),
        ("prop", "toon-banana", toon_cars.banana),
        ("prop", "toon-dash-vents", toon_cars.dash_vents),
        ("prop", "toon-steering-wheel", toon_cars.steering_wheel),
        ("prop", "toon-tally-pad", toon_cars.tally_pad),
    ],
)
def test_the_parts_are_registered(kind, name, builder):
    specimens.load_parts()
    assert registry.get(kind, name).builder is builder


def test_the_default_ledges_are_the_ones_published_reels_use():
    assert {k: toon_house.LEDGES[k] for k in ("oak", "white", "steel")} == {
        "oak": ("#c98f55", "#a56f3e", "#b57d48", "#7c5029"),
        "white": ("#f4f1ea", "#dcd7cc", "#e8e3d8", "#a59f92"),
        "steel": ("#c9d3dc", "#a4b0bc", "#b4bfca", "#73808e"),
    }


@pytest.mark.parametrize("finish", sorted(toon_house.LEDGES))
def test_every_ledge_still_draws(finish):
    cv = canvas()
    toon_house.ledge(cv, cv.comp, finish)


def test_a_passing_vehicle_is_on_screen_only_around_its_moment():
    cv = canvas()
    toon_cars.drive_past(cv, cv.comp, Passing(5.0), y=780.0, id="by")
    node = groups(cv, "by")[0]
    assert 4.0 < float(node.get("start")) < 5.0 < float(node.get("start")) + float(node.get("duration", "9"))


def test_a_bus_takes_longer_to_pass_than_a_car():
    assert toon_cars.pass_seconds(Passing(5.0, "bus")) > toon_cars.pass_seconds(Passing(5.0, "car"))


def test_the_inside_draws_each_vehicle_that_passes():
    cv = canvas()
    toon_cars.car_inside(cv, cv.comp, 0.0, 6.0, passing=(Passing(1.0), Passing(4.0, "bus")))
    assert len([n for n in tree(cv).iter("group") if n.get("start")]) == 2


@pytest.mark.parametrize(
    "bad",
    [Passing(-0.1), Passing(1.0, "tram"), Passing(1.0, "car", "yellow"), Passing(float("nan"))],
    ids=["before-the-reel", "unknown-kind", "named-colour", "nan"],
)
def test_a_passing_vehicle_it_cannot_draw_stops_the_build(bad):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_cars.drive_past(cv, cv.comp, bad, y=780.0)


def test_the_road_needs_a_span():
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_cars.car_inside(cv, cv.comp, 3.0, 3.0)


def test_a_side_car_refuses_a_colour_it_cannot_paint():
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_cars.side_car(cv, cv.comp, colour="yellow")


def test_the_pad_shows_its_count_from_the_start_and_each_new_stroke_at_its_time():
    cv = canvas()
    toon_cars.tally_pad(cv, cv.comp, count=10, strokes=(1.0, 3.0), id="pad")
    drawn = groups(cv, "pad-stroke")
    assert len(drawn) == 10 + 2
    assert [float(n.get("start")) for n in drawn if n.get("start")] == [1.0, 3.0]


def test_a_fifth_stroke_crosses_the_four_before_it():
    assert toon_cars.stroke_line(4)[0][0] < toon_cars.stroke_line(0)[0][0] < toon_cars.stroke_line(3)[1][0]
    assert toon_cars.stroke_line(4)[1][0] > toon_cars.stroke_line(3)[0][0]


def test_two_pads_with_the_same_strokes_draw_the_same_picture():
    def strokes(count, adds):
        return [toon_cars.stroke_line(k) for k in range(count + adds)]

    assert strokes(9, 1) == strokes(10, 0)


@pytest.mark.parametrize(
    ("count", "strokes"),
    [(-1, ()), (31, ()), (30, (1.0,)), (2.5, ()), (2, (3.0, 1.0)), (2, (-1.0,))],
    ids=["negative", "over-the-page", "adds-over-the-page", "not-whole", "out-of-order", "before-the-reel"],
)
def test_a_pad_it_cannot_draw_stops_the_build(count, strokes):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_cars.tally_pad(cv, cv.comp, count=count, strokes=strokes)


def test_a_paw_can_hold_a_pencil_from_either_side():
    cv = canvas()
    toon_world.paw(cv, cv.comp, holding="pencil", side=-1.0)
    toon_world.paw(cv, cv.comp, holding="pencil")


def test_a_wheel_needs_a_radius():
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_cars.steering_wheel(cv, cv.comp, radius=0.0)
