"""The odd props: a pipe, a handwritten sheet, a mosquito, a towel, sheets, a padlock and tasting spoons."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_odds
from srstudio.styles import STYLES
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


@pytest.mark.parametrize(
    "name",
    [
        "toon-pipe",
        "toon-paper-insert",
        "toon-mosquito",
        "toon-rolled-towel",
        "toon-wrestled-sheet",
        "toon-balled-sheets",
        "toon-folded-sheet",
        "toon-padlock",
        "toon-tasting-spoons",
    ],
)
def test_every_prop_is_registered_for_toon(name):
    entry = registry.get("prop", name)
    assert entry.style == "toon" and entry.module == "srstudio.toon_odds"
    assert "toon_odds" in STYLES["toon"].parts


def test_a_mosquito_lives_from_its_first_key_to_its_end():
    cv = canvas()
    toon_odds.mosquito(cv, cv.comp, [(1.0, 100.0, 300.0), (2.0, 200.0, 500.0), (3.0, 200.0, 500.0)], 3.0)
    g = next(g for g in tree(cv).iter("group") if g.get("start"))
    assert float(g.get("start")) == 1.0 and float(g.get("end")) == 3.0


@pytest.mark.parametrize(
    "path, end",
    [([(1.0, 0.0, 0.0)], 4.0), ([(2.0, 0.0, 0.0), (1.0, 0.0, 0.0)], 4.0), ([(5.0, 0.0, 0.0), (6.0, 0.0, 0.0)], 4.0)],
)
def test_a_mosquito_refuses_a_path_it_cannot_fly(path, end):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_odds.mosquito(cv, cv.comp, path, end)


@pytest.mark.parametrize(
    "call",
    [
        lambda cv: toon_odds.rolled_towel(cv, cv.comp, swings=()),
        lambda cv: toon_odds.rolled_towel(cv, cv.comp, start=2.0, end=1.0),
        lambda cv: toon_odds.wrestled_sheet(cv, cv.comp, start=2.0, end=1.0),
        lambda cv: toon_odds.wrestled_sheet(cv, cv.comp, beat=0.0),
        lambda cv: toon_odds.balled_sheets(cv, cv.comp, top=1500.0),
        lambda cv: toon_odds.balled_sheets(cv, cv.comp, start=3.8, end=4.0),
        lambda cv: toon_odds.folded_sheet(cv, cv.comp, start=2.0, end=1.0),
        lambda cv: toon_odds.padlock(cv, cv.comp, start=3.0, opened=1.0),
        lambda cv: toon_odds.tasting_spoons(cv, cv.comp, (1.0, 5.0), end=4.0),
    ],
)
def test_a_prop_refuses_bad_data(call):
    with pytest.raises(ToonDataError):
        call(canvas())


def test_the_spoon_pile_grows_one_spoon_per_cue():
    cv = canvas()
    toon_odds.tasting_spoons(cv, cv.comp, (0.5, 1.0, 1.5), end=4.0)
    assert sorted(float(g.get("start")) for g in tree(cv).iter("group") if g.get("start")) == [0.5, 1.0, 1.5]
