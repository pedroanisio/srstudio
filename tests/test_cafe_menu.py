"""The café's menu board can carry an episode's own prices; without them it draws the shipped board, byte for byte."""

import hashlib
import xml.etree.ElementTree as ET

import pytest

from srstudio import CAFE, locations
from support.signature import TODAY, _canvas


def texts(cv) -> dict[str, str]:
    return {t.get("id"): t.get("text") for t in ET.fromstring(cv.scene.to_bytes()).iter("text")}


def test_the_cafe_keeps_todays_bytes_without_a_menu():
    for kw in ({}, dict(menu=None)):
        cv = _canvas(CAFE)
        locations.cafe(cv, cv.comp, **kw)
        assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == TODAY["cafe"]


def test_a_menu_replaces_the_three_lines_under_the_title_and_nothing_else():
    shipped, priced = _canvas(CAFE), _canvas(CAFE)
    locations.cafe(shipped, shipped.comp)
    locations.cafe(priced, priced.comp, menu=("COFFEE   $3", "PASTRY   $4", "*FEES APPLY"))
    before, after = texts(shipped), texts(priced)
    assert set(before) == set(after)
    changed = {k for k in before if before[k] != after[k]}
    assert changed == {"menu-coffee", "menu-pastry", "menu-wifi"}
    assert (after["menu-coffee"], after["menu-wifi"]) == ("COFFEE   $3", "*FEES APPLY")
    assert after["menu-title"] == "CAFÉ"


@pytest.mark.parametrize(
    "bad",
    [
        ("COFFEE $3", "PASTRY $3"),
        ("COFFEE $3", "PASTRY $3", ""),
        ("COFFEE $3", "PASTRY $3", "X" * (locations.MENU_CHARS + 1)),
        ["COFFEE $3", "PASTRY $3", "FEES"],
        ("COFFEE $3", "PASTRY $3", 3),
    ],
)
def test_the_cafe_refuses_a_menu_its_board_cannot_letter(bad):
    cv = _canvas(CAFE)
    with pytest.raises(locations.LocationError, match="menu"):
        locations.cafe(cv, cv.comp, menu=bad)
