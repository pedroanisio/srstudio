"""Cutout, a reference given from home: each prop draws, is registered, and refuses what it cannot draw."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_reference, registry
from srstudio.cutout_handed import CutoutHandedError
from support.tip_tablet import canvas

CHECKED = CutoutHandedError


def bytes_of(cv) -> str:
    return cv.scene.to_bytes().decode()


@pytest.mark.parametrize("name", ["cue-cards", "banknotes", "robe-and-blazer"])
def test_each_is_a_registered_cutout_prop(name):
    assert registry.get("prop", name)


def test_cue_cards_show_each_word_in_its_span():
    cv = canvas()
    cutout_reference.cue_cards(cv, cv.comp, words=("SEVEN", "VERY"), spans=[(0, 1), (1, 2)])
    drawn = bytes_of(cv)
    assert "SEVEN" in drawn and "VERY" in drawn


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"words": ()}, "1 to 14 characters"),
        ({"words": ("x" * 15,)}, "1 to 14 characters"),
        ({"words": ("A", "B"), "spans": [(0, 1)]}, "2 cards need 2 spans"),
        ({"words": ("A", "B")}, "2 cards need 2 spans"),
        ({"words": ("A",), "spans": [(2, 1)]}, "card spans"),
        ({"scale": 0}, "scale"),
    ],
)
def test_cue_cards_it_cannot_draw_are_refused(kwargs, match):
    cv = canvas()
    with pytest.raises(CHECKED, match=match):
        cutout_reference.cue_cards(cv, cv.comp, **kwargs)


def test_two_bills_are_two_bills():
    cv = canvas()
    cutout_reference.banknotes(cv, cv.comp)
    ids = {e.get("id") for e in ET.fromstring(cv.scene.to_bytes()).iter()}
    assert {"banknotes-0", "banknotes-1"} <= ids and "banknotes-2" not in ids


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"count": 0}, "1 to 5 bills"),
        ({"count": True}, "1 to 5 bills"),
        ({"value": ""}, "1 to 4"),
        ({"scale": 0}, "scale"),
    ],
)
def test_bills_it_cannot_draw_are_refused(kwargs, match):
    cv = canvas()
    with pytest.raises(CHECKED, match=match):
        cutout_reference.banknotes(cv, cv.comp, **kwargs)


def test_the_blazer_goes_over_the_robe():
    cv = canvas()
    cutout_reference.robe_and_blazer(cv, cv.comp)
    drawn = bytes_of(cv)
    assert drawn.index(cutout_reference.ROBE) < drawn.index(cutout_reference.BLAZER)
