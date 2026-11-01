"""Home and table props: each one draws, keeps to its contract and refuses what it cannot be."""

from __future__ import annotations

import pytest

from srstudio import collage, collage_home, collage_sets, registry, show
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


def measure(text: str, size: float = 60.0) -> float:
    return len(text) * size * 0.6


@pytest.mark.parametrize("name", sorted(collage_sets.SHELVES))
def test_a_hook_card_clears_the_shelf_the_bug_and_the_captions_on_every_set(name) -> None:
    cv = canvas()
    x0, y0, x1, y1 = collage_home.hook_box("NO PAD", name, measure)
    sx0, sy0, sx1, sy1 = collage_sets.signature_box(name)
    bx0, by0, bx1, by1 = show.BUG_BOX
    assert x1 <= sx0 or x0 >= sx1 or y1 <= sy0 or y0 >= sy1
    assert x1 <= bx0 or x0 >= bx1 or y1 <= by0 or y0 >= by1
    assert y0 >= collage.CAPTION_BOTTOM
    assert 0 <= x0 < x1 <= cv.width
    assert y1 <= collage.CAPTION_BOTTOM + 180


def test_a_long_hook_takes_the_wide_side_of_a_shelf_on_the_right() -> None:
    x0, _, x1, _ = collage_home.hook_box("INTERVIEW, 9:00", "boardroom", measure)
    assert 0 < x0 and x1 <= collage_sets.signature_box("boardroom")[0]


def test_a_hook_card_shows_only_for_its_seconds() -> None:
    cv = canvas()
    g = collage_home.hook_card(cv, cv.comp, "NO PAD", "cafe", measure, start=0.0, seconds=3.0)
    assert g.id in xml(cv)
    assert "NO PAD" in xml(cv)
    assert 'property="opacity"' in xml(cv)
    assert 'time="3' in xml(cv)


def test_a_hook_card_too_wide_for_the_room_beside_the_shelf_is_refused() -> None:
    with pytest.raises(HomeError, match="too wide"):
        collage_home.hook_box("A HOOK LINE FAR TOO LONG TO SIT BESIDE ANY SHELF AT ALL", "cafe", measure)


@pytest.mark.parametrize("text", ["", "   "])
def test_a_hook_card_refuses_nothing_to_say(text) -> None:
    with pytest.raises(HomeError, match="says nothing"):
        collage_home.hook_box(text, "cafe", measure)


def test_a_hook_card_refuses_no_seconds() -> None:
    cv = canvas()
    with pytest.raises(HomeError, match="positive"):
        collage_home.hook_card(cv, cv.comp, "NO PAD", "cafe", measure, start=0.0, seconds=0.0)


def test_the_booth_is_a_set_with_its_signature_and_no_window() -> None:
    cv = canvas()
    collage_sets.SETS["booth"](cv, cv.comp)
    drawn = xml(cv)
    assert "window" not in drawn and "sky" not in drawn
    x0, y0, x1, y1 = collage_sets.signature_box("booth")
    assert 0 <= x0 < x1 <= cv.width and y1 <= collage.CAPTION_BOTTOM + 300
    assert "collage-booth" in {e.name for e in registry.entries("location")}
