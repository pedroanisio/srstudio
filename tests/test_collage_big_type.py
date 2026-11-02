"""A phone on the largest text size: one, two or three words filling the screen, a page at a time."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import collage_big_type, ink_meter, registry
from srstudio.collage_big_type import BigTypeError, big_type
from support.collage import canvas


def tree(cv):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def sizes(cv):
    root = tree(cv)
    return {t.get("text"): float(t.get("size")) for t in root.iter("text")}


def test_each_word_of_a_page_is_on_a_row_of_its_own_and_shows_from_its_page_until_the_next():
    cv = canvas()
    big_type(cv, cv.comp, 100, 200, 400, 660, pages=((0.0, "GARY LOOKS"), (1.5, "THIN")))
    root = tree(cv)
    assert [t.get("text") for t in root.iter("text")] == ["GARY", "LOOKS", "THIN"]
    keys = [a for a in root.iter("animate") if a.get("property") == "opacity"]
    assert len(keys) == 2


def test_the_type_grows_to_fill_the_screen_and_a_shorter_page_is_bigger():
    cv = canvas()
    big_type(cv, cv.comp, 100, 200, 400, 660, pages=((0.0, "GARY LOOKS"), (1.5, "THIN")))
    got = sizes(cv)
    across = 400 - 2 * collage_big_type.BEZEL
    assert got["GARY"] == got["LOOKS"]
    assert got["THIN"] > got["LOOKS"]
    assert got["LOOKS"] * collage_big_type.CARD_GLYPH * 5 <= across
    assert got["LOOKS"] * collage_big_type.CARD_GLYPH * 5 >= 0.8 * across


def test_a_page_is_as_tall_as_the_screen_lets_it_be():
    cv = canvas()
    big_type(cv, cv.comp, 100, 200, 600, 300, pages=((0.0, "HE GETS SAD"),))
    down = 300 - 2 * collage_big_type.BEZEL
    assert 3 * sizes(cv)["GETS"] * collage_big_type.CARD_LEADING <= down


@pytest.mark.parametrize(
    ("pages", "match"),
    [
        ((), "at least one page"),
        (((1.0, "HI"),), "from second 0"),
        (((0.0, "HI"), (0.0, "NO")), "rising"),
        (((0.0, "HI"), (float("nan"), "NO")), "rising"),
        (((0.0, "   "),), "1 to 3 words"),
        (((0.0, "ONE TWO THREE FOUR"),), "1 to 3 words"),
        (((0.0, "lower case"),), "capitals"),
        (((0.0, "CALL 555"),), "no numbers"),
    ],
)
def test_pages_it_cannot_show_are_refused(pages, match):
    cv = canvas()
    with pytest.raises(BigTypeError, match=match):
        big_type(cv, cv.comp, 100, 200, 400, 660, pages=pages)


def test_a_screen_too_small_to_read_is_refused():
    cv = canvas()
    with pytest.raises(BigTypeError, match="legibility"):
        big_type(cv, cv.comp, 100, 200, 70, 120, pages=((0.0, "UNDERSTANDABLY"),))
    assert collage_big_type.ink_meter.LEGIBLE_PX == ink_meter.LEGIBLE_PX


def test_a_phone_that_cannot_be_drawn_is_refused_before_it_draws():
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(BigTypeError):
        big_type(cv, cv.comp, 100, 200, 40, 660, pages=((0.0, "HI"),))
    assert cv.scene.to_bytes() == before


def test_it_is_registered_with_a_contract_and_returns_the_whole_phone():
    part = registry.describe("prop", "collage-big-type")
    assert part["contract"]["capabilities"]["spatial_attachment"] is False
    cv = canvas()
    g = big_type(cv, cv.comp, 100, 200, 400, 660, pages=((0.0, "HI"),), tilt=-3.0)
    assert tree(cv).find("composition/group").get("id") == g.id
