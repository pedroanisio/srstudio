"""Cutout odds and ends: small things a physical gag turns on."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_odds, registry
from support.tip_tablet import canvas

CHECKED = cutout_odds.CutoutOddsError


def root(cv):
    return ET.fromstring(cv.scene.to_bytes())


def ids(cv) -> set[str]:
    return {e.get("id") for e in root(cv).iter() if e.get("id")}


def errors(cv) -> list:
    return [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message]


DRAWN = [
    ("eaten-sandwich", cutout_odds.eaten_sandwich),
    ("paper-napkin", cutout_odds.paper_napkin),
    ("bistro-table", cutout_odds.bistro_table),
    ("earbud", cutout_odds.earbud),
    ("tin-of-peas", cutout_odds.tin_of_peas),
    ("store-box", cutout_odds.store_box),
]


@pytest.mark.parametrize(("name", "draw"), DRAWN)
def test_each_is_a_registered_cutout_prop_that_draws_cleanly(name, draw):
    entry = registry.get("prop", name)
    assert entry.style == "cutout" and entry.summary
    cv = canvas()
    draw(cv, cv.comp)
    assert not errors(cv)
    assert name in ids(cv)


def test_a_sandwich_has_one_stage_a_bite_and_shows_them_in_turn():
    cv = canvas()
    cutout_odds.eaten_sandwich(cv, cv.comp, bites=[1.0, 3.0, 5.0])
    assert {f"eaten-sandwich-stage-{n}" for n in range(4)} <= ids(cv)
    assert "eaten-sandwich-stage-4" not in ids(cv)
    assert not errors(cv)


def test_an_uneaten_sandwich_has_a_single_stage():
    cv = canvas()
    cutout_odds.eaten_sandwich(cv, cv.comp)
    assert "eaten-sandwich-stage-0" in ids(cv) and "eaten-sandwich-stage-1" not in ids(cv)


@pytest.mark.parametrize(
    ("bad", "match"),
    [
        (dict(bites=[2.0, 1.0]), "rising"),
        (dict(bites=[1.0, 1.0]), "rising"),
        (dict(bites=[-1.0]), "rising"),
        (dict(bites=[1.0, 2.0, 3.0, 4.0]), "three bites"),
        (dict(scale=0), "scale"),
    ],
)
def test_a_sandwich_refuses_what_it_cannot_draw(bad, match):
    cv = canvas()
    with pytest.raises(CHECKED, match=match):
        cutout_odds.eaten_sandwich(cv, cv.comp, **bad)


def test_a_napkin_and_a_table_refuse_a_size_of_nothing():
    cv = canvas()
    with pytest.raises(CHECKED, match="scale"):
        cutout_odds.paper_napkin(cv, cv.comp, scale=0)
    with pytest.raises(CHECKED, match="width"):
        cutout_odds.bistro_table(cv, cv.comp, width=0)


def test_a_flipped_earbud_mirrors_and_keeps_its_size():
    cv = canvas()
    cutout_odds.earbud(cv, cv.comp, 100, 200, scale=2.0, flip=True)
    drawn = next(e for e in root(cv).iter() if e.get("id") == "earbud")
    assert (drawn.get("scaleX"), drawn.get("scaleY")) == ("-2", "2")


@pytest.mark.parametrize("draw", [cutout_odds.earbud, cutout_odds.tin_of_peas, cutout_odds.store_box])
@pytest.mark.parametrize("scale", [0, -1, float("nan"), "big"])
def test_a_store_prop_with_a_scale_it_cannot_take_is_refused(draw, scale):
    cv = canvas()
    with pytest.raises(CHECKED, match="scale"):
        draw(cv, cv.comp, scale=scale)
