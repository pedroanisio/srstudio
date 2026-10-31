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


def test_a_scan_shows_known_things_for_some_seconds():
    cv = canvas()
    assert stick_odds.xray(cv, cv.comp, 2.0, (("chicken", 540.0, 500.0, 1.0),)) is not None
    with pytest.raises(stick.StickDataError, match="seconds"):
        stick_odds.xray(cv, cv.comp, 0.0, (("chicken", 0.0, 0.0, 1.0),))
    with pytest.raises(stick.StickDataError, match="at least one"):
        stick_odds.xray(cv, cv.comp, 2.0, ())
    with pytest.raises(stick.StickDataError, match="unknown scanned item"):
        stick_odds.xray(cv, cv.comp, 2.0, (("bomb", 0.0, 0.0, 1.0),))


def test_a_scan_declares_its_glow_once_however_many_scans_there_are():
    cv = canvas()
    stick_odds.xray(cv, cv.comp, 2.0, (("lasagna", 540.0, 500.0, 1.0),))
    stick_odds.xray(cv, cv.comp, 2.0, (("rolling-pin", 540.0, 500.0, 1.0),))
    assert list(cv._effects) == ["xray-glow"]


@pytest.mark.parametrize("heap", [-1, 4])
def test_a_plate_heaps_three_tiers_at_most(heap):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="tiers"):
        stick_odds.plate(cv, cv.comp, 0, 0, heap=heap)


def test_a_plate_and_a_parcel_need_a_positive_scale():
    cv = canvas()
    for draw in (stick_odds.plate, stick_odds.foil_parcel):
        assert draw(cv, cv.comp, 500, 700) is not None
        with pytest.raises(stick.StickDataError, match="scale"):
            draw(cv, cv.comp, 0, 0, scale=0)


def test_a_robe_is_drawn_once_per_key_and_mirrors_with_the_figure():
    cv = canvas()
    keys = [stick.RigKey(0, "stand"), stick.RigKey(1.0, "stand")]
    plain = stick_odds.robe(cv, cv.comp, keys, 2.0, stick.STANDING)
    flipped = stick_odds.robe(cv, cv.comp, keys, 2.0, stick.STANDING, flip=True)
    assert len(plain.elements()) == len(keys)
    assert float(plain.scaleX) == 1 and float(flipped.scaleX) == -1
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_odds.robe(cv, cv.comp, keys, 2.0, stick.STANDING, scale=0)


def test_the_spoon_the_belt_and_the_note_draw():
    cv = canvas()
    assert stick_odds.spoon(cv, cv.comp, (700, 800), (480, 1100), full=True) is not None
    assert stick_odds.scan_belt(cv, cv.comp) is not None
    assert stick_odds.foil_note(cv, cv.comp, "FOR THE MAN AT SECURITY.") is not None
    with pytest.raises(stick.StickDataError, match="words"):
        stick_odds.foil_note(cv, cv.comp, " ")
