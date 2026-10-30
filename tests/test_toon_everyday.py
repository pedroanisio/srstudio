"""Toon everyday props: the rules every one of them keeps (on the frame, out of the caption band, clear of the
signature marks, its text measured inside its box, its states rising from 0) and each prop in its states."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, TOON, Canvas, Signature, flat_counter, registry, toon, toon_dinner, toon_everyday
from srstudio.toon import ToonDataError, fx, fy
from srstudio.toon_everyday import Screen
from support.toon_bounds import drawn, marks


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def canvas(signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(cv: Canvas, gid: str):
    return next(g for g in tree(cv).iter("group") if g.get("id") == gid)


def texts(node) -> list[str]:
    return [t.get("text") for t in node.iter("text")]


def layer_texts(cv: Canvas, gid: str) -> list[str]:
    """The texts the layers under group ``gid`` show, in drawing order."""
    assets = {t.get("id"): t.get("text") for t in tree(cv).iter("text")}
    return [assets[la.get("asset")] for la in group(cv, gid).iter("layer")]


def keys(node, prop: str) -> list[tuple[float, float]]:
    a = next(a for a in node.findall("animate") if a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]


def frame_box(box) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return fx(x0), fy(y0), fx(x1), fy(y1)


def inside(inner, outer) -> bool:
    return (
        inner.x0 >= outer[0] - 0.01
        and inner.y0 >= outer[1] - 0.01
        and inner.x1 <= outer[2] + 0.01
        and inner.y1 <= outer[3] + 0.01
    )


# -- the signature box -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("front", [toon.desk, toon_dinner.table])
def test_the_signature_box_holds_both_marks_on_the_desk_and_on_the_table(front):
    cv = canvas(signed=True)
    front(cv, cv.comp)
    ids = marks(cv)
    assert [i.split("-")[1] for i in ids] == ["cactus", "code"]
    for gid in ids:
        assert inside(drawn(cv, gid), frame_box(toon_everyday.SIGNATURE_BOX)), gid


# -- placing ---------------------------------------------------------------------------------------------------------
ONE = [Screen(0.0, "off")]


def phone(cv=None, screens=ONE, **kw):
    cv = cv or canvas()
    return toon_everyday.phone(cv, cv.comp, screens, measure=measure, **kw)


def test_a_prop_returns_its_footprint_in_reference_pixels_scaled_about_its_base():
    small, big = phone(at=(300, 700)), phone(at=(300, 700), scale=1.5)
    assert small[0] < 300 < small[2] and small[1] < 700 < small[3]
    assert (big[0] + big[2]) / 2 == pytest.approx((small[0] + small[2]) / 2)
    assert big[3] - 700 == pytest.approx(1.5 * (small[3] - 700))
    assert big[2] - big[0] == pytest.approx(1.5 * (small[2] - small[0]))
    assert big[3] - big[1] == pytest.approx(1.5 * (small[3] - small[1]))


@pytest.mark.parametrize(
    ("at", "match"),
    [
        ((20, 700), "frame"),  # its left edge off the frame
        ((300, 1120), "frame"),  # below the frame
        ((300, 420), "caption"),  # its top in the caption band
        ((480, 860), "signature"),  # its right side over the cactus on the desk
    ],
)
def test_a_prop_stays_on_the_frame_out_of_the_caption_band_and_clear_of_the_signature(at, match):
    with pytest.raises(ToonDataError, match=match):
        phone(at=at)


@pytest.mark.parametrize("scale", [0.5, 2.5, True, math.nan, "1"])
def test_a_prop_scale_keeps_its_lettering_legible_and_on_screen(scale):
    with pytest.raises(ToonDataError, match="scale"):
        phone(at=(300, 800), scale=scale)


@pytest.mark.parametrize("at", [(True, 700), (300, math.inf), (300,), "here", None])
def test_a_prop_stands_at_a_reference_point(at):
    with pytest.raises(ToonDataError, match="at"):
        phone(at=at)


# -- the phone -------------------------------------------------------------------------------------------------------
SCREENS = [
    Screen(0.0, "notify", "Bank", "Paid: $428.60", note="9:41"),
    Screen(1.0, "code", "ENTER CODE", "4 8 _ _", note="Wrong code"),
    Screen(2.0, "profile", "Dana, 34", "Loves hiking\nand tax law"),
    Screen(3.0, "declined", "$42.00", "DECLINED", note="Corner Deli"),
    Screen(4.0, "loading", "Updating...", "1 of 212", fill=0.99),
    Screen(5.0, "off"),
]


def test_each_screen_shows_alone_from_its_second_to_the_next():
    cv = canvas()
    phone(cv, SCREENS, at=(300, 800))
    for k, s in enumerate(SCREENS):
        shown = keys(group(cv, f"phone-screen-{k}"), "opacity")
        on = [(s.at, 1.0)] if s.at == 0 else [(0.0, 0.0), (s.at, 1.0)]
        off = [(SCREENS[k + 1].at, 0.0)] if k + 1 < len(SCREENS) else []
        assert shown == on + off, k


def test_each_screen_letters_its_own_fields():
    cv = canvas()
    phone(cv, SCREENS, at=(300, 800))
    assert layer_texts(cv, "phone-screen-0") == ["9:41", "BANK", "Paid: $428.60"]
    assert layer_texts(cv, "phone-screen-1") == ["ENTER CODE", "4 8 _ _", "Wrong code"]
    assert layer_texts(cv, "phone-screen-2") == ["Dana, 34", "Loves hiking\nand tax law"]
    assert layer_texts(cv, "phone-screen-3") == ["$42.00", "DECLINED", "Corner Deli"]
    assert layer_texts(cv, "phone-screen-4") == ["Updating...", "1 of 212"]
    assert layer_texts(cv, "phone-screen-5") == []


def test_a_notification_buzzes_the_phone_where_it_stands():
    cv = canvas()
    phone(cv, [Screen(0.0, "off"), Screen(2.0, "notify", "Mom", "Call me")], at=(300, 800))
    x = keys(group(cv, "phone"), "x")
    assert x[0] == (0.0, fx(300)) and x[-1][1] == fx(300)
    assert {round(t, 2) for t, v in x if v != fx(300)} <= {2.04, 2.08, 2.12, 2.16, 2.2}
    assert max(abs(v - fx(300)) for _, v in x) > 0


def test_the_loading_bar_fills_to_its_level_by_the_next_screen():
    cv = canvas()
    phone(cv, [Screen(0.0, "loading", "Updating...", fill=0.99), Screen(3.0, "off")], at=(300, 800))
    assert keys(group(cv, "phone-screen-0-bar"), "scaleX") == [(0.0, 0.0), (3.0, 0.99)]


def test_the_last_loading_screen_fills_over_the_fill_time():
    cv = canvas()
    phone(cv, [Screen(0.0, "off"), Screen(1.0, "loading", "Saving", fill=0.5)], at=(300, 800))
    bar = keys(group(cv, "phone-screen-1-bar"), "scaleX")
    assert bar == [(0.0, 0.0), (1.0, 0.0), (1.0 + toon_everyday.FILL_TIME, 0.5)]


def test_a_standing_phone_casts_a_shadow_and_a_held_one_shows_the_thumb_instead():
    standing, held = canvas(), canvas()
    phone(standing, at=(300, 800))
    phone(held, at=(300, 800), hand="#60a7fb")
    fills = lambda cv: [s.get("fill") for s in tree(cv).iter("shape")]  # noqa: E731
    assert "#60a7fb" in fills(held) and "#60a7fb" not in fills(standing)
    assert len(list(tree(standing).iter("shape"))) == len(list(tree(held).iter("shape")))


@pytest.mark.parametrize("hand", [None, "#60a7fb"])
def test_the_phone_draws_inside_its_footprint_in_every_screen(hand):
    cv = canvas()
    box = phone(cv, SCREENS, at=(300, 800), scale=1.4, hand=hand)
    reach = toon_everyday.BUZZ_REACH * 1.4
    assert inside(drawn(cv, "phone"), frame_box((box[0] + reach, box[1], box[2] - reach, box[3])))


@pytest.mark.parametrize(
    ("screens", "match"),
    [
        ([], "at least one"),
        ([Screen(0.5, "off")], "from 0"),
        ([Screen(0.0, "off"), Screen(0.0, "off")], "rising"),
        ([Screen(0.0, "off"), Screen(0.1, "off")], "apart"),
        ([Screen(True, "off")], "second"),
        ([Screen(math.nan, "off")], "second"),
        ([Screen(0.0, "selfie")], "kind"),
        ([("0", "off")], "Screen"),
        ([Screen(0.0, "off", "hello")], "off.*title"),
        ([Screen(0.0, "notify", "Mom")], "notify.*text"),
        ([Screen(0.0, "profile", "Dana", note="x")], "profile.*note"),
        ([Screen(0.0, "code", "PIN", "1234", fill=0.5)], "code.*fill"),
        ([Screen(0.0, "loading", "Saving", fill=1.5)], "fill"),
        ([Screen(0.0, "loading", "Saving", fill=True)], "fill"),
        ([Screen(0.0, "notify", "Mom", "Call me right now please")], "notify.*text.*px"),
        ([Screen(0.0, "profile", "Dana", "one\ntwo\nthree\nfour")], "profile.*text.*lines"),
        ([Screen(0.0, "notify", "Mom", "  ")], "notify.*text"),
        ([Screen(0.0, "notify", 5, "hi")], "notify.*title"),
    ],
)
def test_the_phone_refuses_screens_it_cannot_draw(screens, match):
    with pytest.raises(ToonDataError, match=match):
        phone(screens=screens, at=(300, 800))


def test_the_phone_refuses_a_hand_that_is_not_a_colour():
    with pytest.raises(ToonDataError, match="hand"):
        phone(at=(300, 800), hand="blue")


def test_the_phone_is_registered_with_the_toon_style():
    names = {e["name"]: e for e in registry.catalog(style="toon")}
    assert "toon_everyday" in TOON.parts
    assert (names["toon-phone"]["kind"], names["toon-phone"]["style"]) == ("prop", "toon")
