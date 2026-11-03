"""The cable drawer and what comes with it: it draws on its clock, the street goes out in order, and what cannot happen
is refused."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter
from srstudio.toon import ToonDataError
from srstudio.toon_cables import STREET, cable_drawer, fridge_light, gray_cable, hill_window, kitchen_bin


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=30.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def root(cv: Canvas):
    return cv.group(cv.comp, "root")


def doc(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def animates(cv: Canvas, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in doc(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_drawer_comes_out_when_yanked_and_shuts_when_told():
    cv = canvas()
    cable_drawer(cv, root(cv), 0.2, 20.0)
    keys = animates(cv, "scaleX")[0]
    assert keys[0] == (0.2, 1.0) and keys[1][1] > 1.0
    assert keys[-1][1] == 1.0 and keys[-2][0] == 20.0


def test_the_knot_shows_only_while_the_drawer_is_open():
    cv = canvas()
    cable_drawer(cv, root(cv), 0.2, 20.0)
    inside = [g for g in doc(cv).iter("group") if g.get("start") is not None]
    assert len(inside) == 1 and float(inside[0].get("start")) == 0.2 and float(inside[0].get("end")) > 20.0


@pytest.mark.parametrize(("opens", "closes"), [(-1.0, None), ("x", None), (5.0, 5.05), (5.0, 2.0)])
def test_a_drawer_refuses_a_clock_that_cannot_run(opens, closes):
    cv = canvas()
    with pytest.raises(ToonDataError):
        cable_drawer(cv, root(cv), opens, closes)


def test_a_cable_goes_where_it_is_moved():
    cv = canvas()
    gray_cable(cv, root(cv), ((1.0, 100.0, 300.0), (2.0, 100.0, 800.0)), 1.0, 3.0)
    ys = animates(cv, "y")[0]
    assert ys[0][0] == 1.0 and ys[1][1] > ys[0][1]


@pytest.mark.parametrize(
    ("moves", "start", "end"),
    [
        ((), 0.0, 1.0),
        (((2.0, 1.0, 1.0), (1.0, 1.0, 1.0)), 0.0, 3.0),
        (((1.0, 1.0, "x"),), 0.0, 3.0),
        (((1.0, 1.0, 1.0),), 3.0, 1.0),
    ],
)
def test_a_cable_refuses_moves_it_cannot_make(moves, start, end):
    cv = canvas()
    with pytest.raises(ToonDataError):
        gray_cable(cv, root(cv), moves, start, end)


def test_the_bin_draws_and_refuses_a_bad_place():
    cv = canvas()
    kitchen_bin(cv, root(cv))
    with pytest.raises(ToonDataError):
        kitchen_bin(cv, root(cv), at="here")


def test_the_lights_go_out_in_order_and_come_back_together():
    cv = canvas()
    out = tuple(1.0 + 0.3 * k for k in range(len(STREET)))
    hill_window(cv, root(cv), out, 12.0)
    tracks = [k for k in animates(cv, "opacity") if len(k) == 3]
    lights = [k for k in tracks if k[1][0] != out[-1]]
    assert min(k[1][0] for k in tracks if k[1][1] == 0.0) == out[0]
    assert all(k[2] == (12.0, 1.0) for k in tracks)
    assert lights


def test_a_quiet_window_has_no_keys():
    cv = canvas()
    hill_window(cv, root(cv))
    assert animates(cv, "opacity") == []


@pytest.mark.parametrize(
    ("out", "on"),
    [
        ((1.0, 2.0), None),
        (tuple(range(len(STREET), 0, -1)), None),
        (tuple(1.0 + k for k in range(len(STREET))), 3.0),
        ((), -1.0),
    ],
)
def test_a_street_refuses_an_order_it_cannot_keep(out, on):
    cv = canvas()
    with pytest.raises(ToonDataError):
        hill_window(cv, root(cv), out, on)


def test_the_fridge_light_goes_with_the_power_and_comes_back():
    cv = canvas()
    fridge_light(cv, root(cv), 11.6, 21.8)
    assert animates(cv, "opacity") == [[(0.0, 1.0), (11.6, 0.0), (21.8, 1.0)]]


@pytest.mark.parametrize(("off", "on"), [(-1.0, None), (None, 3.0), (5.0, 2.0)])
def test_a_fridge_light_refuses_a_clock_that_cannot_run(off, on):
    cv = canvas()
    with pytest.raises(ToonDataError):
        fridge_light(cv, root(cv), off, on)
