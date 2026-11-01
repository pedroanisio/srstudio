"""The Collage odds: a slice that halves, an eye chart, a lens frame, a sensor tap, a leaf, a glass, a jug, a scale."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, collage_odds, flat_counter, registry
from srstudio.collage_odds import CollageOddsError
from srstudio.styles import STYLES


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def shapes(cv: Canvas) -> int:
    return sum(1 for e in tree(cv).iter() if e.tag.rsplit("}", 1)[-1] not in ("group", "scene", "project"))


@pytest.mark.parametrize(
    "name",
    [
        "collage-cake-slice",
        "collage-eye-chart",
        "collage-lens-frame",
        "collage-sensor-tap",
        "collage-spinach",
        "collage-full-glass",
        "collage-water-jug",
        "collage-doctor-scale",
    ],
)
def test_every_prop_is_registered_for_collage(name):
    entry = registry.get("prop", name)
    assert entry.style == "collage" and entry.module == "srstudio.collage_odds"
    assert "collage_odds" in STYLES["collage"].parts


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv: collage_odds.cake_slice(cv, cv.comp, 500, 500, (1.0, 2.0)),
        lambda cv: collage_odds.eye_chart(cv, cv.comp, 200, 400, ("E", "FP"), (1.0, 2.0), 6.0, 5.0),
        lambda cv: collage_odds.lens_frame(cv, cv.comp, 500, 500),
        lambda cv: collage_odds.sensor_tap(cv, cv.comp, 500, 1500, ((1.0, 2.0),)),
        lambda cv: collage_odds.spinach(cv, cv.comp, 500, 500),
        lambda cv: collage_odds.wine_glass(cv, cv.comp, 500, 1500),
        lambda cv: collage_odds.water_jug(cv, cv.comp, 500, 1500),
        lambda cv: collage_odds.doctor_scale(cv, cv.comp, 400, 1880, 3.0, 1100.0, 6.0),
    ],
)
def test_every_prop_draws_something_valid(draw):
    cv = canvas()
    draw(cv)
    assert shapes(cv) > 0


def test_a_tap_runs_only_in_its_runs():
    dry, wet = canvas(), canvas()
    collage_odds.sensor_tap(dry, dry.comp, 500, 1500)
    collage_odds.sensor_tap(wet, wet.comp, 500, 1500, ((1.0, 2.0),))
    assert shapes(wet) > shapes(dry)


def test_the_height_bar_can_start_lower_to_clear_what_stands_behind_it():
    def top(**kw) -> float:
        cv = canvas()
        collage_odds.doctor_scale(cv, cv.comp, 400, 1880, **kw)
        return min(float(r.get("y")) for r in tree(cv).iter("shape") if r.get("shape") == "rect")

    assert top(bar_from=790.0) > top()
    assert top(bar_from=620.0) == top()


@pytest.mark.parametrize("bar_from", [619.0, 1880.0, float("nan")])
def test_the_height_bar_stays_on_the_scale(bar_from):
    with pytest.raises(CollageOddsError):
        collage_odds.doctor_scale(canvas(), canvas().comp, 400, 1880, bar_from=bar_from)


def test_a_scale_without_a_drop_stays_where_it_is_drawn():
    cv = canvas()
    collage_odds.doctor_scale(cv, cv.comp, 400, 1880)
    assert shapes(cv) > 0


@pytest.mark.parametrize(
    "draw",
    [
        lambda cv: collage_odds.cake_slice(cv, cv.comp, 500, 500, (2.0, 1.0)),
        lambda cv: collage_odds.eye_chart(cv, cv.comp, 200, 400, ("E",), (1.0, 2.0), 6.0, 5.0),
        lambda cv: collage_odds.doctor_scale(cv, cv.comp, 400, 1880, 7.0, 1100.0, 6.0),
    ],
)
def test_a_prop_refuses_cues_it_cannot_play(draw):
    with pytest.raises(CollageOddsError):
        draw(canvas())
