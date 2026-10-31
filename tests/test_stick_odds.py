"""The Stick odds and ends: each draws, and each refuses what it cannot draw."""

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_odds
from srstudio.canvas import Signature


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


def test_the_aisle_is_signed_like_any_location():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background="#d9d2c4")
    cv = Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"), signature=Signature())
    stick_odds.aisle(cv, cv.comp)
    assert cv._sig_ids["sig-cactus"] == 1 and cv._sig_ids["sig-code"] == 1


def test_a_queue_turns_inside_its_shot_and_fits_the_aisle():
    cv = canvas()
    assert stick_odds.queue(cv, cv.comp, 2.0, turn=1.0, rows=3) is not None
    with pytest.raises(stick.StickDataError, match="inside the shot"):
        stick_odds.queue(cv, cv.comp, 2.0, turn=3.0)
    with pytest.raises(stick.StickDataError, match="rows"):
        stick_odds.queue(cv, cv.comp, 2.0, turn=1.0, rows=0)


def test_a_book_is_open_or_shut_and_a_bag_needs_a_scale():
    cv = canvas()
    assert len(stick_odds.book(cv, cv.comp, 0, 0).elements()) > len(
        stick_odds.book(cv, cv.comp, 0, 0, shut=True).elements()
    )
    for draw in (stick_odds.book, stick_odds.duffel):
        with pytest.raises(stick.StickDataError, match="scale"):
            draw(cv, cv.comp, 0, 0, scale=-1)


def test_a_double_take_looks_looks_away_and_lands():
    look, away, land = stick.Face("open"), stick.Face("half"), stick.Face("wide")
    keys = stick_odds.double_take(1.0, "stand", look, away, land, step=0.5)
    assert [key.start for key in keys] == [1.0, 1.5, 2.0]
    assert [key.face for key in keys] == [look, away, land]
    assert {key.pose for key in keys} == {"stand"}


def test_a_double_take_fits_a_rig_after_the_first_key():
    cv = canvas()
    keys = [
        stick.RigKey(0, "stand"),
        *stick_odds.double_take(0.5, "stand", stick.Face(), stick.Face("half"), stick.Face()),
    ]
    assert stick.rig(cv, cv.comp, keys, 2.0, poses=stick.STANDING) is not None


@pytest.mark.parametrize("step", [0.0, -1.0])
def test_a_double_take_needs_time(step):
    with pytest.raises(stick.StickDataError, match="step"):
        stick_odds.double_take(0.0, "stand", stick.Face(), stick.Face(), stick.Face(), step=step)


def test_a_double_take_starts_in_the_shot():
    with pytest.raises(stick.StickDataError, match="starts in the shot"):
        stick_odds.double_take(-0.1, "stand", stick.Face(), stick.Face(), stick.Face())
