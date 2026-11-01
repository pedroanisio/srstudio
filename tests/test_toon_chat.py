"""A chat on a phone and the chip on it: each refuses what it cannot letter, and nothing shows before its time."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_chat
from srstudio.toon import ToonDataError
from srstudio.toon_chat import Bubble


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def measure(text: str, size: float) -> float:
    return len(text) * size * 0.5


def texts(cv: Canvas) -> list[str]:
    return [n.get("text", "") or (n.text or "") for n in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("text")]


CHAT = (Bubble(0.0, "Leave him and open a candle shop."),)


@pytest.mark.parametrize(
    ("name", "builder"), [("toon-chat-phone", toon_chat.chat_phone), ("toon-chat-chip", toon_chat.chat_chip)]
)
def test_the_parts_are_registered(name: str, builder) -> None:
    assert registry.get("prop", name).builder is builder


def test_a_long_message_wraps_on_the_screen_with_every_word_kept() -> None:
    rows = toon_chat.wrapped("Leave him and open a candle shop.", measure, 26, 160)
    assert " ".join(rows) == "Leave him and open a candle shop."
    assert all(measure(r, 26) <= 160 for r in rows)
    assert len(rows) > 1


def test_a_word_wider_than_the_bubble_is_refused() -> None:
    with pytest.raises(ToonDataError, match="wider"):
        toon_chat.wrapped("Supercalifragilistic", measure, 26, 100)


def test_a_chat_too_long_for_the_screen_is_refused() -> None:
    cv = canvas()
    long = (Bubble(0.0, "word " * 60),)
    with pytest.raises(ToonDataError, match="screen"):
        toon_chat.chat_phone(cv, cv.comp, long, measure=measure)


def test_bubbles_arrive_in_order() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="rise"):
        toon_chat.chat_phone(cv, cv.comp, (Bubble(2.0, "a"), Bubble(1.0, "b")), measure=measure)


def test_a_phone_stays_out_of_the_caption_band_and_off_the_marks() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="caption"):
        toon_chat.chat_phone(cv, cv.comp, CHAT, measure=measure, at=(300.0, 400.0))
    with pytest.raises(ToonDataError, match="signature|marks"):
        toon_chat.chat_phone(cv, cv.comp, CHAT, measure=measure, at=(490.0, 860.0))


def test_a_phone_turned_away_shows_its_back_until_it_turns() -> None:
    cv = canvas()
    g = toon_chat.chat_phone(cv, cv.comp, CHAT, measure=measure, face_from=5.0)
    xml = cv.scene.to_bytes(layout="pretty").decode()
    assert 'property="visible"' in xml or 'property="opacity"' in xml
    assert g is not None


def test_a_face_from_past_nothing_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="face_from"):
        toon_chat.chat_phone(cv, cv.comp, CHAT, measure=measure, face_from=-1.0)


def test_a_buzz_shakes_the_phone_at_its_second() -> None:
    cv = canvas()
    toon_chat.chat_phone(cv, cv.comp, CHAT, measure=measure, buzz=(4.0,))
    assert 'property="x"' in cv.scene.to_bytes(layout="pretty").decode()


def test_a_chip_is_lettered_and_gated() -> None:
    cv = canvas()
    toon_chat.chat_chip(cv, cv.comp, "You're absolutely right", 4.0, 6.0, measure=measure, at=(150.0, 760.0))
    xml = cv.scene.to_bytes(layout="pretty").decode()
    assert "You're absolutely right" in xml or "You&apos;re absolutely right" in xml
    assert 'start="4' in xml


@pytest.mark.parametrize(
    ("text", "start", "end", "match"),
    [("", 1.0, 2.0, "text"), ("ok", 2.0, 1.0, "start"), ("x" * 200, 1.0, 2.0, "wide")],
)
def test_a_chip_refuses_what_it_cannot_show(text: str, start: float, end: float, match: str) -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_chat.chat_chip(cv, cv.comp, text, start, end, measure=measure, at=(296.0, 700.0))
