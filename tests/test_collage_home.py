"""Home and table props: each one draws, keeps to its contract and refuses what it cannot be."""

from __future__ import annotations

import pytest

from srstudio import collage_home, registry
from srstudio.collage_home import HomeError
from support.collage_photo import canvas


def xml(cv) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


DRAWN = [
    (collage_home.hard_hat, (540, 700)),
    (collage_home.kayak, (540, 900)),
    (collage_home.school_desk, (540, 1200)),
    (collage_home.staircase, (200, 1400, 680, 620)),
    (collage_home.pay_envelope, (540, 960)),
    (collage_home.headset, (540, 1090)),
    (collage_home.desk_lamp, (540, 1200)),
    (collage_home.dead_plant, (540, 1200)),
    (collage_home.cereal_bowl, (540, 1200)),
    (collage_home.spoon, (540, 1200)),
    (collage_home.pen, (540, 1200)),
    (collage_home.menu_card, (540, 960)),
    (collage_home.order_pad, (540, 960)),
    (collage_home.plate, (540, 960)),
    (collage_home.chair_back, (540, 560)),
    (collage_home.wall_hole, (540, 960)),
    (collage_home.snowy_window, (110, 400, 300, 400)),
    (collage_home.toothbrush_mug, (540, 1300)),
    (collage_home.napkin, (540, 1300)),
]


@pytest.mark.parametrize(("draw", "args"), DRAWN, ids=lambda v: getattr(v, "__name__", ""))
def test_a_prop_draws_something(draw, args) -> None:
    cv = canvas()
    empty = len(xml(cv))
    draw(cv, cv.comp, *args)
    assert len(xml(cv)) > empty + 100


def test_the_props_are_parts_of_the_collage_style() -> None:
    names = {e.name for e in registry.entries("prop")}
    assert {"collage-wall-tv", "collage-pay-envelope", "collage-wall-hole", "collage-napkin"} <= names


def test_a_tv_hands_back_a_clipped_screen_smaller_than_the_set() -> None:
    cv = canvas()
    tv = collage_home.wall_tv(cv, cv.comp, 40, 830, 1000)
    assert (tv.w, tv.h) == (956.0, 576.0)
    assert "mask" in xml(cv)


@pytest.mark.parametrize("stamp", ["$90,000", "CONFIDENTIAL 2026", "1"])
def test_a_sealed_envelope_refuses_any_figure(stamp) -> None:
    cv = canvas()
    with pytest.raises(HomeError, match="no figure"):
        collage_home.pay_envelope(cv, cv.comp, 540, 960, stamp=stamp)


def test_a_plate_refuses_a_dish_it_has_no_drawing_of() -> None:
    cv = canvas()
    with pytest.raises(HomeError, match="no dish"):
        collage_home.plate(cv, cv.comp, 540, 960, dish="tiramisu")


@pytest.mark.parametrize("steps", [1, 0, 2.5, "six"])
def test_a_staircase_refuses_a_step_count_that_is_no_flight(steps) -> None:
    cv = canvas()
    with pytest.raises(HomeError, match="at least 2 steps"):
        collage_home.staircase(cv, cv.comp, 0, 0, 300, 300, steps=steps)


@pytest.mark.parametrize("lines", [-1, 1.5])
def test_a_pad_refuses_a_line_count_that_is_not_whole(lines) -> None:
    cv = canvas()
    with pytest.raises(HomeError, match="whole number"):
        collage_home.order_pad(cv, cv.comp, 0, 0, lines=lines)


@pytest.mark.parametrize(
    "call",
    [
        lambda cv: collage_home.wall_tv(cv, cv.comp, 0, 0, 0),
        lambda cv: collage_home.hard_hat(cv, cv.comp, 0, 0, -1),
        lambda cv: collage_home.pay_envelope(cv, cv.comp, 0, 0, size=0),
        lambda cv: collage_home.wall_hole(cv, cv.comp, 0, 0, float("nan")),
    ],
)
def test_a_size_that_is_not_positive_is_refused(call) -> None:
    with pytest.raises(HomeError, match="positive"):
        call(canvas())
