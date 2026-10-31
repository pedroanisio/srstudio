"""The Stick odds and ends: each draws, and each refuses what it cannot draw."""

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_odds


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


def test_a_poster_needs_lettering_a_size_and_the_font():
    cv = canvas()
    assert stick_odds.poster(cv, cv.comp, 100, 100, 400, 300, "STRETCH WITH NOOR") is not None
    with pytest.raises(stick.StickDataError, match="lettering"):
        stick_odds.poster(cv, cv.comp, 0, 0, 400, 300, "  ")
    with pytest.raises(stick.StickDataError, match="size"):
        stick_odds.poster(cv, cv.comp, 0, 0, 0, 300, "X")


def test_a_headset_mirrors_with_the_figure():
    cv = canvas()
    right = stick_odds.headset(cv, cv.comp, 500, 700)
    left = stick_odds.headset(cv, cv.comp, 500, 700, flip=True)
    assert float(right.scaleX) == 1 and float(left.scaleX) == -1
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_odds.headset(cv, cv.comp, 0, 0, scale=0)
