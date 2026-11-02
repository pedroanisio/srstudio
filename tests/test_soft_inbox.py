"""Soft inbox: the phone screens of a mail reel, each refusing what it cannot show."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, registry, soft_inbox
from srstudio.soft_inbox import Count
from srstudio.soft_props import SoftPropError
from support.soft_props import canvas


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def groups(cv: Canvas) -> dict:
    return {g.get("id"): g for g in tree(cv).iter("group")}


def test_the_module_is_a_part_of_the_soft_style():
    assert "soft_inbox" in SOFT.parts
    names = {e.name for e in registry.entries()}
    assert {"soft-mail-screen", "soft-mail-list", "soft-call-screen"} <= names


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
