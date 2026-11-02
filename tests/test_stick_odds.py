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


def test_a_queue_stands_on_legs_only_when_a_shot_shows_them():
    def drawn(**kw) -> str:
        cv = canvas()
        stick_odds.queue(cv, cv.comp, 2.0, turn=1.0, rows=2, **kw)
        return cv.scene.to_bytes(layout="pretty").decode()

    assert stick_odds.TROUSERS in drawn(legs=True)
    assert stick_odds.TROUSERS not in drawn()


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


def test_a_bin_can_lose_its_wheels_but_no_more():
    cv = canvas()
    assert stick_odds.wheelie_bin(cv, cv.comp, 500, 900, wheels=0) is not None
    with pytest.raises(stick.StickDataError, match="wheels"):
        stick_odds.wheelie_bin(cv, cv.comp, 0, 0, wheels=3)
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_odds.wheelie_bin(cv, cv.comp, 0, 0, scale=0)


def test_a_truck_and_a_slipper_need_a_positive_scale():
    cv = canvas()
    for draw in (stick_odds.trash_truck, stick_odds.slipper):
        assert draw(cv, cv.comp, 100, 900) is not None
        with pytest.raises(stick.StickDataError, match="scale"):
            draw(cv, cv.comp, 0, 0, scale=-1)


def test_sparks_turn_about_and_refuse_what_cannot_flicker():
    cv = canvas()
    group = stick_odds.sparks(cv, cv.comp, 500, 900, 1.0)
    assert len(group.elements()) == 2
    with pytest.raises(stick.StickDataError, match="seconds"):
        stick_odds.sparks(cv, cv.comp, 0, 0, 0.0)
    with pytest.raises(stick.StickDataError, match="rate"):
        stick_odds.sparks(cv, cv.comp, 0, 0, 1.0, rate=0)
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_odds.sparks(cv, cv.comp, 0, 0, 1.0, scale=0)


def test_a_wardrobe_half_up_shows_its_mistake_and_a_finished_one_does_not():
    half, done = canvas(), canvas()
    stick_odds.wardrobe(half, half.comp, 100, 1500, "half")
    stick_odds.wardrobe(done, done.comp, 100, 1500, "done")
    assert b"THIS SIDE IN" in half.scene.to_bytes(layout="pretty")
    assert b"THIS SIDE IN" not in done.scene.to_bytes(layout="pretty")


def test_a_wardrobe_has_only_its_stages():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="stage"):
        stick_odds.wardrobe(cv, cv.comp, 100, 1500, "nearly")
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_odds.wardrobe(cv, cv.comp, 100, 1500, "done", scale=0)


@pytest.mark.parametrize("drawing", [d for d in stick_odds.MANUAL_DRAWINGS if d != "argument"])
def test_a_manual_page_is_wordless_but_for_its_number(drawing):
    cv = canvas()
    stick_odds.manual_page(cv, cv.comp, 14, drawing)
    assert b'text="14"' in cv.scene.to_bytes(layout="pretty")


def test_the_speech_bubble_belongs_on_the_argument_page_and_only_there():
    cv = canvas()
    stick_odds.manual_page(cv, cv.comp, 9, "argument", bubble="YOU SAID YOU MEASURED")
    assert b"YOU SAID YOU MEASURED" in cv.scene.to_bytes(layout="pretty")
    with pytest.raises(stick.StickDataError, match="bubble"):
        stick_odds.manual_page(cv, cv.comp, 9, "argument")
    with pytest.raises(stick.StickDataError, match="bubble"):
        stick_odds.manual_page(cv, cv.comp, 14, "sofa", bubble="NO")


def test_a_manual_page_refuses_what_a_manual_does_not_have():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="draws one of"):
        stick_odds.manual_page(cv, cv.comp, 3, "dragon")
    with pytest.raises(stick.StickDataError, match="start at 1"):
        stick_odds.manual_page(cv, cv.comp, 0, "sofa")


def test_a_ringing_phone_says_who_and_only_shakes_when_it_rings():
    still, ringing = canvas(), canvas()
    stick_odds.caller(still, still.comp, 540, 960, "MOM")
    stick_odds.caller(ringing, ringing.comp, 540, 960, "MOM", ring=(0.0, 0.5))
    assert b"MOM" in still.scene.to_bytes(layout="pretty")
    assert ringing.scene.to_bytes(layout="pretty") != still.scene.to_bytes(layout="pretty")
    with pytest.raises(stick.StickDataError, match="who is calling"):
        stick_odds.caller(still, still.comp, 540, 960, "  ")
    with pytest.raises(stick.StickDataError, match="in order"):
        stick_odds.caller(still, still.comp, 540, 960, "MOM", ring=(2.0, 1.0))


def test_screws_count_and_small_props_refuse_a_bad_scale():
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="at least one"):
        stick_odds.screws(cv, cv.comp, 0, 0, count=0)
    for draw in (stick_odds.screws, stick_odds.drill, stick_odds.planks):
        with pytest.raises(stick.StickDataError, match="scale"):
            draw(cv, cv.comp, 0, 0, scale=-1)


def test_a_book_takes_a_cover_colour():
    plain, manual = canvas(), canvas()
    stick_odds.book(plain, plain.comp, 0, 0)
    stick_odds.book(manual, manual.comp, 0, 0, colour="#f4f1ea")
    assert b"#f4f1ea" in manual.scene.to_bytes(layout="pretty")
    assert b"#f4f1ea" not in plain.scene.to_bytes(layout="pretty")


def test_a_carton_stands_on_its_foot_and_refuses_a_size_it_cannot_draw():
    cv = canvas()
    g = stick_odds.carton(cv, cv.comp, 300, 1500, w=200, h=160)
    assert float(g.x) == 300 and float(g.y) == 1500
    assert stick_odds.carton(cv, cv.comp, 300, 1500, flip=True, scale=0.8) is not None
    with pytest.raises(stick.StickDataError, match="size"):
        stick_odds.carton(cv, cv.comp, 0, 0, w=0)
    with pytest.raises(stick.StickDataError, match="size"):
        stick_odds.carton(cv, cv.comp, 0, 0, h=-4)
    with pytest.raises(stick.StickDataError, match="scale"):
        stick_odds.carton(cv, cv.comp, 0, 0, scale=0)


def test_a_carton_stacked_on_another_casts_no_shadow_on_the_air():
    cv = canvas()
    plain = stick_odds.carton(cv, cv.comp, 300, 1500)
    high = stick_odds.carton(cv, cv.comp, 300, 1300, shadow=False)
    assert len(high.nodes) == len(plain.nodes) - 1


def test_a_carton_carries_no_lettering():
    cv = canvas()
    stick_odds.carton(cv, cv.comp, 300, 1500)
    assert b"<layer" not in cv.scene.to_bytes()


def test_a_receipt_hangs_from_its_top_and_unrolls_on_a_rising_span():
    cv = canvas()
    stick_odds.receipt(cv, cv.comp, 100, 200, 500)
    assert b"scaleY" not in cv.scene.to_bytes()
    rolling = stick_odds.receipt(cv, cv.comp, 100, 200, 500, unroll=(1.0, 1.8))
    assert float(rolling.anchorY) == 0
    assert b"scaleY" in cv.scene.to_bytes()
    with pytest.raises(stick.StickDataError, match="length"):
        stick_odds.receipt(cv, cv.comp, 0, 0, 0)
    with pytest.raises(stick.StickDataError, match="width"):
        stick_odds.receipt(cv, cv.comp, 0, 0, 100, w=0)
    with pytest.raises(stick.StickDataError, match="unroll"):
        stick_odds.receipt(cv, cv.comp, 0, 0, 100, unroll=(2.0, 1.0))


def test_a_receipt_has_no_readable_figures():
    cv = canvas()
    stick_odds.receipt(cv, cv.comp, 100, 200, 500)
    assert b"<layer" not in cv.scene.to_bytes()


def test_unlettered_half_wardrobe_fails_before_drawing():
    from srstudio.canvas import CanvasError

    cv = canvas()
    cv.font_asset = None
    before = cv.scene.to_bytes()
    with pytest.raises(CanvasError):
        stick_odds.wardrobe(cv, cv.comp, 100, 1400, stage="half")
    assert cv.scene.to_bytes() == before
    cv.font_asset = "inter"
    stick_odds.wardrobe(cv, cv.comp, 100, 1400, stage="half")
    fresh = canvas()
    stick_odds.wardrobe(fresh, fresh.comp, 100, 1400, stage="half")
    assert cv.scene.to_bytes() == fresh.scene.to_bytes()
