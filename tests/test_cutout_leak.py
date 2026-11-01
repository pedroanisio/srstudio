"""What a town does with your news: a lettered takeaway cup, a crayon page, a cake knife and a slice."""

from __future__ import annotations

import pytest

from srstudio import cutout_leak
from srstudio.cutout_leak import CutoutLeakError
from srstudio.registry import get
from support.tip_tablet import canvas


def test_a_cup_reads_the_lines_it_is_given():
    cv = canvas()
    cutout_leak.lettered_cup(cv, cv.comp, lines=("GOOD LUCK", "AT THE BANK"))
    text = cv.scene.to_bytes().decode()
    assert "GOOD LUCK" in text and "AT THE BANK" in text


@pytest.mark.parametrize("lines", [(), ("A", "B", "C", "D"), ("",), ("  ",), ("X" * 13,), "GOOD LUCK", (1,)], ids=str)
def test_a_cup_refuses_lines_it_cannot_letter(lines):
    cv = canvas()
    with pytest.raises(CutoutLeakError):
        cutout_leak.lettered_cup(cv, cv.comp, lines=lines)


@pytest.mark.parametrize(
    "build", [cutout_leak.lettered_cup, cutout_leak.crayon_page, cutout_leak.cake_knife, cutout_leak.cake_slice]
)
@pytest.mark.parametrize("scale", [0, -1, "big", float("nan")])
def test_every_prop_refuses_a_scale_it_cannot_draw(build, scale):
    cv = canvas()
    with pytest.raises(CutoutLeakError, match="scale"):
        build(cv, cv.comp, scale=scale)


def test_the_crayon_page_letters_nothing():
    cv = canvas()
    cutout_leak.crayon_page(cv, cv.comp)
    assert "<text" not in cv.scene.to_bytes().decode()


@pytest.mark.parametrize("name", ["lettered-cup", "crayon-page", "cake-knife", "cake-slice"])
def test_each_prop_is_registered_for_the_catalog(name):
    assert get("prop", name) is not None
