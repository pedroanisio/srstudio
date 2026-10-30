"""Toon props and sets: the meeting room, the mug, the clock, the notes, the toasts, the board, the logo, the badge."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import TOON, Canvas, registry, toon, toon_props
from support.toon_props import canvas, measure


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def paths(cv: Canvas):
    return [s for s in tree(cv).iter("shape") if s.get("shape") == "path"]


def animations(cv: Canvas, prop: str):
    return [a for a in tree(cv).iter("animate") if a.get("property") == prop]


def keys_of(a):
    return [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]


def test_the_meeting_room_puts_a_whiteboard_where_the_window_was():
    cv = canvas()
    toon_props.meeting(cv, cv.comp)
    rects = [s for s in tree(cv).iter("shape") if s.get("shape") == "rect"]
    boxes = [(float(r.get("x")), float(r.get("y")), float(r.get("width")), float(r.get("height"))) for r in rects]
    assert boxes[0] == (0, 0, 1080, 1920)  # the wall
    frame = boxes[1]
    assert frame[0] == pytest.approx(toon.fx(333)) and frame[1] == pytest.approx(toon.fy(262))
    x, y, w, h = toon_props.BOARD_BOX
    assert boxes[2] == pytest.approx((toon.fx(x), toon.fy(y), toon.fh(w), toon.fh(h)))
    assert x > 333 and x + w < 663 and y > 262 and y + h < 733  # the board sits inside the frame
    assert toon_props.TOAST_X + toon_props.TOAST_W <= toon.REF_W  # the toast stays in the frame
    assert len(paths(cv)) == 1  # the chair


def test_the_mug_steams_only_in_its_spans():
    cv = canvas()
    toon_props.mug(cv, cv.comp, steam=[(1.0, 2.0), (4.0, 5.0)])
    (gate,) = animations(cv, "opacity")
    assert keys_of(gate) == [(0, 0), (1, 1), (2, 0), (4, 1), (5, 0)]
    assert len(paths(cv)) == 4  # the handle and three wisps
    silent = canvas()
    toon_props.mug(silent, silent.comp)
    assert animations(silent, "opacity") == [] and len(paths(silent)) == 1
    with pytest.raises(toon.ToonDataError, match="steam spans"):
        toon_props.mug(canvas(), cv.comp, steam=[(2.0, 1.0)])


def test_clock_angles_and_the_hands_jumping_to_each_time():
    assert toon_props.clock_angles("09:00") == (270.0, 0.0)
    assert toon_props.clock_angles("12:30") == (15.0, 180.0)
    assert toon_props.clock_angles("21:15") == (277.5, 90.0)
    for bad in ("9", "25:00", "09:60", "nine"):
        with pytest.raises(toon.ToonDataError, match="HH:MM"):
            toon_props.clock_angles(bad)
    cv = canvas()
    toon_props.clock(cv, cv.comp, [(1.0, "09:00"), (3.0, "09:01"), (4.5, "09:30")])
    hour, minute = animations(cv, "rotation")
    assert hour.get("defaultInterpolation") == "hold" and hour.get("timeBase") is None
    assert keys_of(hour) == [(0, 270), (1, 270), (3, 270.5), (4.5, 285)]
    assert keys_of(minute) == [(0, 0), (1, 0), (3, 6), (4.5, 180)]
    with pytest.raises(toon.ToonDataError, match="rising"):
        toon_props.clock(canvas(), cv.comp, [(2.0, "09:00"), (1.0, "09:01")])
    with pytest.raises(toon.ToonDataError, match="rising"):
        toon_props.clock(canvas(), cv.comp, [])


def test_notes_are_short_texts_on_tilted_squares():
    cv = canvas()
    toon_props.notes(cv, cv.comp, ["REPORT!", "9 AM", "DO NOT", "FORGET"])
    t = tree(cv)
    turned = [g for g in t.iter("group") if g.get("rotation")]
    assert [float(g.get("rotation")) for g in turned] == [-7, 6, 5, -6]
    assert [a.get("text") for a in t.iter("text")] == ["REPORT!", "9 AM", "DO NOT", "FORGET"]
    for texts, match in (
        ([], "one to four"),
        (["a"] * 5, "one to four"),
        (["x" * 11], "10 characters"),
        ([" "], "short"),
    ):
        with pytest.raises(toon.ToonDataError, match=match):
            toon_props.notes(canvas(), cv.comp, texts)


def test_a_toast_slides_in_shakes_with_the_buzz_and_holds_to_its_end():
    cv = canvas()
    items = [toon_props.Toast(1.0, 3.0, "Rex", "THE REPORT. 9 AM."), toon_props.Toast(4.0, 6.0, "Fern", "??")]
    toon_props.toasts(cv, cv.comp, items)
    t = tree(cv)
    cards = [g for g in t.find("composition").findall("group") if g.get("start")]
    assert [(g.get("start"), g.get("end")) for g in cards] == [("1", "3"), ("4", "6")]
    assert [a.get("text") for a in t.iter("text")] == ["REX", "THE REPORT. 9 AM.", "FERN", "??"]
    first, second = animations(cv, "x")
    assert first.get("defaultInterpolation") == "linear"
    keys = keys_of(first)
    assert keys[0] == (1.0, pytest.approx(toon.fh(toon_props.TOAST_W + 60))) and keys[1] == (1.25, 0)
    assert len(keys) == 2 + len(toon_props.BUZZ_SHAKE) - 1 and keys[-1] == (pytest.approx(1.49), 0)
    assert keys_of(second)[0][0] == 4.0
    for bad, match in (
        (toon_props.Toast(2.0, 1.0, "Rex", "x"), "start < end"),
        (toon_props.Toast(0.0, 1.0, "", "x"), "sender"),
        (toon_props.Toast(0.0, 1.0, "Rex", "x" * 25), "at most 24"),
    ):
        with pytest.raises(toon.ToonDataError, match=match):
            toon_props.toasts(canvas(), cv.comp, [bad])


def test_a_gated_toast_letters_its_card_only_once_the_card_has_landed_on_frame():
    items = [toon_props.Toast(1.0, 3.0, "Rex", "THE REPORT. 9 AM."), toon_props.Toast(4.0, 6.0, "Fern", "??")]
    cv = canvas()
    toon_props.toasts(cv, cv.comp, items, gated=True)
    cards = [g for g in tree(cv).find("composition").findall("group") if g.get("start")]
    for toast, card in zip(items, cards, strict=True):
        (lettering,) = [g for g in card.iter("group") if g.findall("layer")]
        landed = toast.start + toon_props.TOAST_SLIDE
        assert (float(lettering.get("start")), float(lettering.get("end"))) == (landed, toast.end)
        assert keys_of(next(a for a in card.iter("animate") if a.get("property") == "x"))[1] == (landed, 0)
    assert toon_props.TOAST_X + toon_props.TOAST_W <= toon.REF_W  # landed, the card is wholly on frame
    plain, gated = canvas(), canvas()
    toon_props.toasts(plain, plain.comp, items)
    toon_props.toasts(gated, gated.comp, items, gated=False)
    assert gated.scene.to_bytes() == plain.scene.to_bytes()  # ungated by default: published toasts are unchanged


def test_a_gated_toast_lasts_long_enough_for_its_lettering_to_be_read():
    least = toon_props.TOAST_SLIDE + toon_props.TOAST_READ
    cv = canvas()
    toon_props.toasts(cv, cv.comp, [toon_props.Toast(1.0, 1.0 + least, "Rex", "??")], gated=True)
    with pytest.raises(toon.ToonDataError, match=f"toast 0: gated, it lasts at least {least} s"):
        toon_props.toasts(cv, cv.comp, [toon_props.Toast(1.0, 1.0 + least - 0.01, "Rex", "??")], gated=True)
    toon_props.toasts(cv, cv.comp, [toon_props.Toast(1.0, 1.5, "Rex", "??")])  # ungated, as before


def test_board_text_is_marker_blue_inside_the_board_and_may_be_timed():
    cv = canvas()
    toon_props.board_text(cv, cv.comp, "LOGO v1", start=1.0, end=3.0)
    t = tree(cv)
    (g,) = [g for g in t.find("composition").findall("group")]
    assert (g.get("start"), g.get("end")) == ("1", "3")
    (text,) = t.iter("text")
    assert text.get("color") == toon_props.MARKER and text.get("text") == "LOGO v1"
    layer = g.find("layer")
    x, y, w, _ = toon_props.BOARD_BOX
    assert float(layer.get("x")) == pytest.approx(toon.fx(x + 10)) and float(layer.get("y")) == pytest.approx(
        toon.fy(y + 14)
    )
    # the board runs off the right edge: the text wraps inside the part on screen, with a margin to spare
    assert float(layer.get("x")) + float(text.get("width")) <= 1080 - toon.fh(10)
    assert toon.fx(x + 10) + toon.fh(w - 20) > 1080
    always = canvas()
    toon_props.board_text(always, always.comp, "Q3")
    assert tree(always).find("composition").find("group").get("start") is None
    with pytest.raises(toon.ToonDataError, match="1 to 40"):
        toon_props.board_text(canvas(), cv.comp, "x" * 41)


def test_scale_keys_hold_each_size_and_ramp_to_the_next():
    assert toon_props.scale_keys([(0.0, 1.0)]) == [(0.0, 1.0)]
    assert toon_props.scale_keys([(0.0, 1.0), (2.0, 1.6), (4.0, 2.4)], grow=0.3) == [
        (0.0, 1.0),
        (2.0, 1.0),
        (2.3, 1.6),
        (4.0, 1.6),
        (4.3, 2.4),
    ]
    assert toon_props.scale_keys([(1.0, 2.0)], grow=0.5)[:3] == [(0.0, 2.0), (1.0, 2.0), (1.5, 2.0)]
    with pytest.raises(toon.ToonDataError, match="apart"):
        toon_props.scale_keys([(0.0, 1.0), (0.1, 2.0)], grow=0.3)
    with pytest.raises(toon.ToonDataError, match="positive"):
        toon_props.scale_keys([(0.0, 0.0)])


@pytest.mark.parametrize("grow", [0.0, -0.3, float("nan"), float("inf"), True])
def test_scale_keys_refuse_a_grow_that_is_not_a_positive_number_of_seconds(grow):
    with pytest.raises(toon.ToonDataError, match="grow"):
        toon_props.scale_keys([(0.0, 1.0), (2.0, 1.6)], grow=grow)


def test_the_logo_grows_about_its_centre_and_its_shadow_shows_through_its_span():
    cv = canvas()
    toon_props.logo(cv, cv.comp, [(0.0, 1.0), (2.0, 2.0), (4.0, 5.0)], shadow=(3.0, 5.5))
    t = tree(cv)
    scaled = [g for g in t.iter("group") if g.get("anchorX")]
    assert len(scaled) == 2 and all(
        float(g.get("anchorX")) == pytest.approx(toon.fx(toon_props.LOGO_CENTRE[0])) for g in scaled
    )
    xs, ys = animations(cv, "scaleX"), animations(cv, "scaleY")
    assert len(xs) == len(ys) == 2 and all(a.get("defaultInterpolation") == "linear" for a in xs + ys)
    assert keys_of(xs[1]) == [(0, 1), (2, 1), (2.3, 2), (4, 2), (4.3, 5)]
    (shadow,) = animations(cv, "opacity")
    assert keys_of(shadow) == [(0, 0), (3, 0.35), (5.5, 0)]
    plain = canvas()
    toon_props.logo(plain, plain.comp)
    assert len(animations(plain, "scaleX")) == 1 and animations(plain, "opacity") == []
    shapes = list(tree(plain).iter("shape"))
    assert len(shapes) == 8 + 2 + 2 + 1  # rays, rim and disc, eyes, smile
    with pytest.raises(toon.ToonDataError, match="shadow"):
        toon_props.logo(canvas(), cv.comp, shadow=(2.0, 1.0))


def test_the_badge_sits_under_the_pill_sized_by_its_text():
    cv = canvas()
    toon_props.badge(cv, cv.comp, "Fern calling", 0.5, 4.0, measure)
    t = tree(cv)
    g = t.find("composition").find("group")
    assert (g.get("start"), g.get("end")) == ("0.5", "4")
    rect = g.find("shape")
    assert float(rect.get("width")) == pytest.approx(measure("FERN CALLING") + toon.fh(56))
    assert float(rect.get("y")) == pytest.approx(toon.fy(toon_props.BADGE_TOP))
    assert toon_props.BADGE_TOP >= toon.CAPTION_TOP + toon.CAPTION_H  # never over the caption pill
    assert toon_props.TOAST_Y >= toon_props.BADGE_TOP + 36  # nor the toast over the badge
    (text,) = t.iter("text")
    assert text.get("text") == "FERN CALLING"
    with pytest.raises(toon.ToonDataError, match="1 to 30"):
        toon_props.badge(canvas(), cv.comp, "", 0.0, 1.0, measure)
    with pytest.raises(toon.ToonDataError, match="start < end"):
        toon_props.badge(canvas(), cv.comp, "x", 1.0, 1.0, measure)


def test_the_props_are_registered_with_the_toon_style():
    names = {e["name"]: e for e in registry.catalog(style="toon")}
    assert "toon_props" in TOON.parts
    expected = {
        "toon-meeting": "location",
        "toon-mug": "prop",
        "toon-clock": "prop",
        "toon-notes": "prop",
        "toon-toast": "graphic",
        "toon-board-text": "graphic",
        "toon-logo": "graphic",
        "toon-badge": "graphic",
    }
    for name, kind in expected.items():
        assert (names[name]["kind"], names[name]["style"]) == (kind, "toon"), name
