"""The cleaned flat: what opens, what comes out, and refusal of data none of it can draw."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_flat
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def drawn(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def keyed(cv: Canvas, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in drawn(cv).iter("animate")
        if a.get("property") == prop
    ]


@pytest.mark.parametrize(
    "name",
    ["toon-closet", "toon-oven", "toon-shower", "toon-front-door", "toon-laundry-pile", "toon-tiny-drawer"]
    + ["toon-whirl", "toon-sparkles", "toon-plates", "toon-flat"],
)
def test_each_part_draws_with_no_data_of_its_own(name):
    entry = next(e for e in registry.entries() if e.name == name)
    cv = canvas()
    entry.builder(cv, cv.group(cv.comp, "g"))
    assert len(list(drawn(cv).find("composition").iter())) > 2


@pytest.mark.parametrize("part", [toon_flat.closet, toon_flat.oven, toon_flat.shower, toon_flat.front_door])
@pytest.mark.parametrize("at", [-1.0, float("nan"), "soon", None])
def test_an_opening_needs_a_real_second(part, at):
    cv = canvas()
    with pytest.raises(ToonDataError, match="opens at a second"):
        part(cv, cv.group(cv.comp, "g"), at)


def test_the_closet_stays_shut_until_its_second():
    cv = canvas()
    toon_flat.closet(cv, cv.group(cv.comp, "g"), 2.0)
    assert keyed(cv, "scaleX") == [[(0.0, 1.0), (2.0, 1.0), (2.0 + toon_flat.BURST, 0.14)]]


@pytest.mark.parametrize(("count", "start", "step"), [(0, 0.0, 0.1), (3, 0.0, 0.0), (1.5, 0.0, 0.1), (3, "now", 0.1)])
def test_plates_refuse_bad_counts_and_steps(count, start, step):
    cv = canvas()
    with pytest.raises(ToonDataError, match="plates need"):
        toon_flat.plates(cv, cv.group(cv.comp, "g"), start, count, step)


def test_plates_must_finish_by_the_end_and_may_finish_exactly_on_it():
    cv = canvas()
    g = cv.group(cv.comp, "g")
    with pytest.raises(ToonDataError, match="do not finish"):
        toon_flat.plates(cv, g, 1.0, 3, 0.5, end=2.0)
    toon_flat.plates(cv, g, 1.0, 3, 0.5, end=2.0 + toon_flat.PLATE_RUN)
    assert len(keyed(cv, "x")) == 3


@pytest.mark.parametrize("top", [100.0, 1000.0, float("nan")])
def test_a_pile_stands_in_the_frame(top):
    cv = canvas()
    with pytest.raises(ToonDataError, match="stands between"):
        toon_flat.pile(cv, cv.group(cv.comp, "g"), top)


def test_a_pile_needs_time_to_rise():
    cv = canvas()
    with pytest.raises(ToonDataError, match="rises in"):
        toon_flat.pile(cv, cv.group(cv.comp, "g"), 600.0, 3.9, 4.0)


def test_a_settled_pile_does_not_move():
    cv = canvas()
    toon_flat.pile(cv, cv.group(cv.comp, "g"), 600.0, None)
    assert keyed(cv, "y") == []


def test_a_rising_pile_lands_where_it_was_asked():
    cv = canvas()
    toon_flat.pile(cv, cv.group(cv.comp, "g"), 600.0, 1.0)
    (keys,) = keyed(cv, "y")
    assert keys[0][1] > 0 and keys[-1] == (1.0 + toon_flat.RISE, 0.0)


def test_a_tiny_drawer_needs_time_for_its_sock():
    cv = canvas()
    with pytest.raises(ToonDataError, match="tiny drawer needs"):
        toon_flat.tiny_drawer(cv, cv.group(cv.comp, "g"), 3.9, 4.0)


@pytest.mark.parametrize(("start", "end"), [(1.0, 1.1), (-1.0, 1.0), ("a", 2.0)])
def test_a_whirl_refuses_a_span_it_cannot_spin_in(start, end):
    cv = canvas()
    with pytest.raises(ToonDataError, match="a whirl spins"):
        toon_flat.whirl(cv, cv.group(cv.comp, "g"), start, end)


def test_a_whirl_is_slow_and_close_in_tone_so_it_does_not_flash():
    cv = canvas()
    toon_flat.whirl(cv, cv.group(cv.comp, "g"), 0.0, 0.7)
    (keys,) = keyed(cv, "rotation")
    assert abs(keys[-1][1] - keys[0][1]) / 0.7 <= 900.0


def test_sparkles_refuse_a_span_that_does_not_run_forward():
    cv = canvas()
    with pytest.raises(ToonDataError, match="sparkles run"):
        toon_flat.sparkles(cv, cv.group(cv.comp, "g"), 2.0, 2.0)
