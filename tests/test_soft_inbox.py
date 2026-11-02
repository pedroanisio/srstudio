"""Soft inbox: the phone screens of a mail reel, each refusing what it cannot show."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, registry, soft_inbox
from srstudio.soft_inbox import Count, Level
from srstudio.soft_props import SoftPropError
from support.soft_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas) -> dict:
    return {g.get("id"): g for g in tree(cv).iter("group")}


def test_the_module_is_a_part_of_the_soft_style():
    assert "soft_inbox" in SOFT.parts
    names = {e.name for e in registry.entries()}
    assert {"soft-mail-screen", "soft-mail-list", "soft-call-screen", "soft-battery-screen"} <= names


def opacity(group) -> list[tuple[float, float]]:
    animate = next(a for a in group if a.tag.endswith("animate") and a.get("property") == "opacity")
    return [(float(k.get("time")), float(k.get("value"))) for k in animate]


def test_a_badge_shows_each_count_only_for_its_own_span():
    cv = canvas()
    soft_inbox.mail_screen(cv, cv.comp, counts=(Count("41,382", 0.0, 0.9), Count("41,383", 0.9, 1.8)))
    found = groups(cv)
    assert opacity(found["soft-mail-screen-count-0"]) == [(0.0, 1.0), (0.9, 0.0)]
    assert opacity(found["soft-mail-screen-count-1"]) == [(0.0, 0.0), (0.9, 1.0), (1.8, 0.0)]


def test_a_list_keeps_every_row_on_the_glass():
    cv = canvas()
    soft_inbox.mail_list(cv, cv.comp, marked=2)
    rows = [s for s in tree(cv).iter("shape") if s.get("height") == "52"]
    assert len(rows) == 3
    assert all(float(r.get("y")) >= -130 and float(r.get("y")) + 52 <= 130 for r in rows)


def test_a_scrolled_list_moves_its_page_smoothly_and_nothing_else():
    cv = canvas()
    soft_inbox.mail_list(cv, cv.comp, scroll=((0.0, 14.0), (0.3, 0.0)))
    found = groups(cv)
    animate = [a for a in found["soft-mail-list-page"] if a.tag.endswith("animate")]
    assert [a.get("property") for a in animate] == ["y"] and animate[0].get("defaultInterpolation") != "hold"
    assert not [a for a in found["soft-mail-list"] if a.tag.endswith("animate")]


def test_only_a_press_darkens_the_red_button():
    cv = canvas()
    soft_inbox.call_screen(cv, cv.comp, pressed=1.2)
    assert opacity(groups(cv)["soft-call-screen-pressed"])[:2] == [(0.0, 0.0), (1.2, 1.0)]
    cv = canvas()
    soft_inbox.call_screen(cv, cv.comp)
    assert "soft-call-screen-pressed" not in groups(cv)


@pytest.mark.parametrize(
    "kw",
    [
        dict(counts=()),
        dict(counts=(Count("", 0.0, 1.0),)),
        dict(counts=(Count("41,382,000", 0.0, 1.0),)),
        dict(counts=(Count("1", 1.0, 1.0),)),
        dict(counts=(Count("1", 0.0, 1.0), Count("2", 0.5, 2.0))),
        dict(scale=0),
        dict(x=float("nan")),
    ],
)
def test_a_mail_screen_refuses(kw):
    cv = canvas()
    g = cv.comp
    with pytest.raises(SoftPropError):
        soft_inbox.mail_screen(cv, g, **kw)


@pytest.mark.parametrize(
    "kw",
    [
        dict(rows=()),
        dict(rows=("a", "b", "c", "d", "e")),
        dict(rows=("",)),
        dict(rows=("A SUBJECT LONGER THAN ANY ROW HOLDS",)),
        dict(rows=("ONE\nTWO\nTHREE",)),
        dict(rows=("a",), marked=1),
        dict(scroll=((1.0, 0.0), (0.5, 3.0))),
        dict(scale=-1),
    ],
)
def test_a_mail_list_refuses(kw):
    cv = canvas()
    g = cv.comp
    with pytest.raises(SoftPropError):
        soft_inbox.mail_list(cv, g, **kw)


@pytest.mark.parametrize(
    "kw",
    [
        dict(caller=""),
        dict(caller="A CALLER WITH TOO LONG A NAME"),
        dict(caller="A\nB\nC"),
        dict(pressed="soon"),
        dict(scale=0),
    ],
)
def test_a_call_screen_refuses(kw):
    cv = canvas()
    g = cv.comp
    with pytest.raises(SoftPropError):
        soft_inbox.call_screen(cv, g, **kw)


def test_a_battery_shows_each_level_only_for_its_own_span_and_goes_red_when_low():
    cv = canvas()
    soft_inbox.battery_screen(cv, cv.comp, levels=(Level(41, 0.0, 0.9), Level(2, 0.9, 1.8)))
    found = groups(cv)
    assert opacity(found["soft-battery-screen-level-0"]) == [(0.0, 1.0), (0.9, 0.0)]
    assert opacity(found["soft-battery-screen-level-1"]) == [(0.0, 0.0), (0.9, 1.0), (1.8, 0.0)]
    texts = {t.get("id"): t.get("text") for t in tree(cv).iter() if t.get("text") is not None}
    assert texts == {"soft-battery-screen-text-0": "41%", "soft-battery-screen-text-1": "2%"}
    fills = {
        k: [s.get("fill") for s in found[f"soft-battery-screen-level-{k}"].iter("shape") if s.get("fill")]
        for k in (0, 1)
    }
    assert soft_inbox.BATTERY_OK in fills[0] and soft_inbox.BADGE in fills[1]


def test_a_battery_fill_is_as_wide_as_its_charge_with_a_sliver_left_at_the_bottom():
    assert soft_inbox.charge_width(100) == soft_inbox.CELL[2]
    assert soft_inbox.charge_width(50) == soft_inbox.CELL[2] / 2
    assert 0 < soft_inbox.charge_width(0) == soft_inbox.SLIVER < soft_inbox.charge_width(2) + 1


def test_a_level_can_show_its_charge_without_the_number_for_a_phone_near_the_frame_edge():
    cv = canvas()
    soft_inbox.battery_screen(cv, cv.comp, levels=(Level(41, 0.0, 0.9, number=False), Level(2, 0.9, 1.8)))
    found = {g.get("id"): g for g in tree(cv).iter() if g.get("id")}
    assert "soft-battery-screen-text-0" not in found
    assert "soft-battery-screen-text-1" in found
    assert len([s for s in found["soft-battery-screen-level-0"].iter("shape")]) == 1


def test_a_battery_screen_shows_no_status_bar_only_the_cell_and_its_number():
    cv = canvas()
    soft_inbox.battery_screen(cv, cv.comp, levels=(Level(2, 0.0, 1.0),))
    words = [t.get("text") for t in tree(cv).iter() if t.get("text") is not None]
    assert words == ["2%"]


@pytest.mark.parametrize(
    "kw",
    [
        dict(levels=()),
        dict(levels=(Level(101, 0.0, 1.0),)),
        dict(levels=(Level(-1, 0.0, 1.0),)),
        dict(levels=(Level(True, 0.0, 1.0),)),
        dict(levels=(Level(2.5, 0.0, 1.0),)),
        dict(levels=(Level(2, 0.0, 1.0, number=1),)),
        dict(levels=(Level(2, 1.0, 1.0),)),
        dict(levels=(Level(2, 0.0, float("inf")),)),
        dict(levels=(Level(41, 0.0, 1.0), Level(33, 0.5, 2.0))),
        dict(scale=0),
        dict(y=float("nan")),
    ],
)
def test_a_battery_screen_refuses(kw):
    cv = canvas()
    g = cv.comp
    with pytest.raises(SoftPropError):
        soft_inbox.battery_screen(cv, g, **kw)


def number_boxes(cv: Canvas) -> dict[str, tuple[float, float]]:
    """Each battery number's box: its left edge on the glass, and its width."""
    root = tree(cv)
    widths = {t.get("id"): float(t.get("width")) for t in root.iter("text")}
    return {
        layer.get("asset"): (float(layer.get("x")), widths[layer.get("asset")])
        for layer in root.iter("layer")
        if layer.get("asset") in widths
    }


def test_a_battery_number_measured_in_the_reel_s_font_has_a_box_only_as_wide_as_the_number():
    """The engine keeps a text's box, not its letters, inside the safe area: a box as wide as the glass put a phone's
    2% outside it at the frame edge while the 2% itself sat inside, so the reel drew no number there."""
    cv = canvas()
    soft_inbox.battery_screen(
        cv,
        cv.comp,
        levels=(Level(2, 0.0, 1.0), Level(100, 1.0, 2.0)),
        measure=lambda text, size: 0.5 * size * len(text),
    )
    pad = soft_inbox.NUMBER_PAD
    assert number_boxes(cv) == {
        "soft-battery-screen-text-0": pytest.approx((-(46 + 2 * pad) / 2, 46 + 2 * pad)),
        "soft-battery-screen-text-1": pytest.approx((-(92 + 2 * pad) / 2, 92 + 2 * pad)),
    }


def test_a_battery_number_without_a_measure_keeps_the_glass_wide_box():
    cv = canvas()
    soft_inbox.battery_screen(cv, cv.comp, levels=(Level(2, 0.0, 1.0),))
    assert number_boxes(cv) == {"soft-battery-screen-text-0": (-60.0, 120.0)}


@pytest.mark.parametrize("width", [0.0, -3.0, float("nan"), 200.0])
def test_a_battery_number_refuses_a_measure_it_cannot_box_on_the_glass(width):
    cv = canvas()
    with pytest.raises(SoftPropError, match="number"):
        soft_inbox.battery_screen(cv, cv.comp, levels=(Level(2, 0.0, 1.0),), measure=lambda text, size: width)
