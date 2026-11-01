"""The one short line a Cutout reel opens on."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import cutout_key
from srstudio.fonts import text_width
from srstudio.show import BUG_BOX
from support.tip_tablet import canvas

FONT = next(Path("/usr/share/fonts").rglob("DejaVuSans-Bold.ttf")).read_bytes()


def bar(cv) -> ET.Element:
    root = ET.fromstring(cv.scene.to_bytes())
    group = next(e for e in root.iter() if e.get("id") == "key-line")
    return next(e for e in group.iter() if e.get("shape") == "rect")


def test_the_bar_is_as_wide_as_its_words_in_the_reels_own_font():
    cv = canvas()
    cutout_key.key_line(cv, cv.comp, "ONE POSITION", 0.0, 2.6, font=FONT)
    width = float(bar(cv).get("width"))
    assert width == pytest.approx(text_width(FONT, "ONE POSITION", cutout_key.SIZE) + cutout_key.PAD, abs=0.01)


def test_it_shows_only_between_its_times():
    cv = canvas()
    node = cutout_key.key_line(cv, cv.comp, "ONE POSITION", 0.2, 2.6, font=FONT)
    assert (node.start, node.end) == (0.2, 2.6)


def test_the_default_place_is_under_the_shows_bug():
    assert cutout_key.TOP >= BUG_BOX[3]


@pytest.mark.parametrize("text", ["", "   ", "A LINE MUCH TOO LONG TO SIT ON ONE BAR OF A PHONE"])
def test_a_line_that_cannot_sit_on_the_bar_is_refused(text):
    cv = canvas()
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.key_line(cv, cv.comp, text, 0.0, 2.0, font=FONT)


@pytest.mark.parametrize("span", [(-1.0, 2.0), (2.0, 2.0), (3.0, 2.0), (0.0, float("inf"))])
def test_a_span_that_ends_before_it_starts_is_refused(span):
    cv = canvas()
    with pytest.raises(cutout_key.CutoutKeyError):
        cutout_key.key_line(cv, cv.comp, "ONE POSITION", *span, font=FONT)


def test_it_never_sits_on_the_bug():
    cv = canvas()
    with pytest.raises(cutout_key.CutoutKeyError, match="bug"):
        cutout_key.key_line(cv, cv.comp, "M" * 15, 0.0, 2.0, font=FONT, top=240)
