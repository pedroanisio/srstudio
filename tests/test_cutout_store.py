"""Cutout at a big-box store: the aisle, the cart and its contents, the checkout, and the dark at home."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_store, registry
from support.tip_tablet import canvas

CHECKED = cutout_store.CutoutStoreError


def ids(cv) -> set[str]:
    return {e.get("id") for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("id")}


def errors(cv) -> list:
    return [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message]


DRAWN = [
    ("hand-basket", cutout_store.hand_basket),
    ("shopping-cart", cutout_store.shopping_cart),
    ("table-lamp", cutout_store.table_lamp),
    ("taper-candles", cutout_store.taper_candles),
    ("step-ladder", cutout_store.step_ladder),
    ("kayak", cutout_store.kayak),
    ("paddle", cutout_store.paddle),
    ("life-ring", cutout_store.life_ring),
    ("dark-eyes", cutout_store.dark_eyes),
    ("light-switch", cutout_store.light_switch),
]


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        *(("prop", name) for name, _ in DRAWN),
        ("prop", "long-receipt"),
        ("prop", "checkout-lane"),
        ("prop", "shelf-goods"),
        ("location", "store-aisle"),
    ],
)
def test_each_is_a_registered_cutout_part(kind, name):
    entry = registry.get(kind, name)
    assert entry.style == "cutout" and entry.summary


@pytest.mark.parametrize(("name", "draw"), DRAWN)
def test_a_prop_draws_and_refuses_a_bad_scale(name, draw):
    cv = canvas()
    draw(cv, cv.comp)
    assert name in ids(cv) and errors(cv) == []
    with pytest.raises(CHECKED, match="scale"):
        draw(cv, cv.comp, scale=0, id=f"{name}-bad")


def test_goods_stand_inside_the_cart():
    cv = canvas()
    cutout_store.shopping_cart(cv, cv.comp, contents=lambda g: cutout_store.table_lamp(cv, g, id="in-the-cart"))
    assert "in-the-cart" in ids(cv) and errors(cv) == []


def test_a_rider_sits_between_the_cockpit_and_the_near_side():
    cv = canvas()
    rider = []
    cutout_store.kayak(cv, cv.comp, rider=rider.append)
    assert len(rider) == 1 and errors(cv) == []


@pytest.mark.parametrize("bad", [{"length": 0}, {"beam": -1}])
def test_a_kayak_refuses_a_hull_it_cannot_have(bad):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_store.kayak(cv, cv.comp, **bad)


def test_a_paddle_refuses_no_length():
    cv = canvas()
    with pytest.raises(CHECKED, match="length"):
        cutout_store.paddle(cv, cv.comp, length=0)


def test_a_ladder_refuses_no_height():
    cv = canvas()
    with pytest.raises(CHECKED, match="height"):
        cutout_store.step_ladder(cv, cv.comp, height=0)


def test_eyes_blink_and_glance_on_cue():
    cv = canvas()
    cutout_store.dark_eyes(cv, cv.comp, blinks=[(1.0, 1.2), (2.0, 2.2)], glances=[(0.0, 0.0), (1.0, -20.0)])
    assert {"dark-eyes-open", "dark-eyes-pupils"} <= ids(cv) and errors(cv) == []


@pytest.mark.parametrize("bad", [{"blinks": [(2.0, 1.0)]}, {"blinks": [(2.0, 3.0), (1.0, 1.5)]}, {"glances": ()}])
def test_eyes_refuse_cues_that_do_not_run_in_order(bad):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_store.dark_eyes(cv, cv.comp, **bad)


def test_a_switch_flips_on_each_cue():
    cv = canvas()
    cutout_store.light_switch(cv, cv.comp, flips=(1.0, 2.0, 3.0))
    assert "light-switch-rocker" in ids(cv) and errors(cv) == []


@pytest.mark.parametrize("flips", [(2.0, 1.0), (1.0, 1.0), (-1.0,), ("soon",), ("soon", 1.0)])
def test_a_switch_refuses_flips_out_of_order(flips):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_store.light_switch(cv, cv.comp, flips=flips)


def test_a_receipt_prints_over_its_span():
    cv = canvas()
    cutout_store.long_receipt(cv, cv.comp, printing=(1.0, 3.0))
    assert "long-receipt" in ids(cv) and errors(cv) == []


@pytest.mark.parametrize("bad", [{"length": 0}, {"printing": (3.0, 1.0)}])
def test_a_receipt_refuses_what_cannot_print(bad):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_store.long_receipt(cv, cv.comp, **bad)


def test_a_checkout_lane_runs_its_belt():
    cv = canvas()
    cutout_store.checkout_lane(cv, cv.comp, running=(0.5, 2.0))
    assert "checkout-lane-marks" in ids(cv) and errors(cv) == []
    with pytest.raises(CHECKED):
        cutout_store.checkout_lane(cv, cv.comp, running=(2.0, 1.0), id="backwards")


def test_shelves_are_the_same_from_a_seed_and_need_a_drift():
    def drawn(seed):
        cv = canvas()
        cutout_store.shelf_goods(cv, cv.comp, seed=seed, width=800)
        return cv.scene.to_bytes()

    assert drawn(3) == drawn(3) != drawn(4)
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_store.shelf_goods(cv, cv.comp, drift=())
    with pytest.raises(CHECKED):
        cutout_store.shelf_goods(cv, cv.comp, width=0)


def test_the_aisle_calls_its_slots():
    cv = canvas()
    called = []
    cutout_store.store_aisle(cv, cv.comp, in_aisle=called.append, front=called.append, shots=[(0.0, 2.0)])
    assert len(called) == 2 and errors(cv) == []
