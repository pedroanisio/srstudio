"""The Ink phone: a chat with a contact, bubbles that arrive on the shot's clock, the delivery status under the last
of mine, the typing dots, and the refusals for what the screen cannot show."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_phone, registry, shared_counter
from srstudio.canvas import Signature
from srstudio.ink_phone import Bubble, PhoneError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


def opacity_keys(cv: Canvas):
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "opacity"
    ]


def test_the_chat_shows_the_contact_the_bubbles_and_the_status_in_turn():
    cv = canvas()
    ink_phone.phone(
        cv,
        cv.comp,
        "Boss",
        [Bubble("the boss is SO boring"), Bubble("Agreed.", mine=False, at=2.0)],
        status=[(0.0, "sending"), (1.0, "failed")],
    )
    shown = texts(cv)
    assert "Boss" in shown and "the boss is SO boring" in shown and "Agreed." in shown
    assert ink_phone.STATUS_TEXT["sending"] in shown and ink_phone.STATUS_TEXT["failed"] in shown
    keys = opacity_keys(cv)
    assert [(0.0, 0.0), (2.0, 1.0)] in keys  # their reply arrives at 2 s
    assert [(0.0, 1.0), (1.0, 0.0)] in keys and [(0.0, 0.0), (1.0, 1.0)] in keys  # sending, then failed


def test_a_status_replaced_before_my_bubble_arrives_never_shows():
    cv = canvas()
    bubbles = [Bubble("hi", mine=False), Bubble("u up?", at=2.0)]
    ink_phone.phone(cv, cv.comp, "Boss", bubbles, status=[(0.5, "sending"), (1.0, "sent")])
    shown = texts(cv)
    assert ink_phone.STATUS_TEXT["sent"] in shown and ink_phone.STATUS_TEXT["sending"] not in shown
    assert [(0.0, 0.0), (2.0, 1.0)] in opacity_keys(cv)  # sent, from the bubble on; nothing over it
    cv = canvas()
    ink_phone.phone(cv, cv.comp, "Boss", bubbles, status=[(0.5, "sending"), (2.5, "sent")])
    keys = opacity_keys(cv)
    assert [(0.0, 0.0), (2.0, 1.0), (2.5, 0.0)] in keys and [(0.0, 0.0), (2.5, 1.0)] in keys  # in turn


def test_the_typing_dots_pulse_only_in_their_span():
    cv = canvas()
    ink_phone.phone(cv, cv.comp, "Boss", [Bubble("hi")], typing=(0.5, 2.0))
    keys = opacity_keys(cv)
    assert [(0.0, 0.0), (0.5, 1.0), (2.0, 0.0)] in keys  # the typing bubble, on and off
    pulses = [k for k in keys if len(k) > 3]
    assert len(pulses) == 3
    for dot in pulses:
        assert all(0.5 <= t <= 2.0 for t, _ in dot)


def test_a_full_screen_and_bad_data_are_refused():
    cv = canvas()
    with pytest.raises(PhoneError, match="contact"):
        ink_phone.phone(cv, cv.comp, "", [Bubble("hi")])
    with pytest.raises(PhoneError, match="contact"):
        ink_phone.phone(cv, cv.comp, "X" * (ink_phone.CONTACT_MAX + 1), [Bubble("hi")])
    with pytest.raises(PhoneError, match="at least one"):
        ink_phone.phone(cv, cv.comp, "Boss", [])
    with pytest.raises(PhoneError, match="1 to"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("x" * (ink_phone.TEXT_MAX + 1))])
    with pytest.raises(PhoneError, match="in order"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a", at=2.0), Bubble("b", at=1.0)])
    with pytest.raises(PhoneError, match="seconds"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a", at=-1.0)])
    with pytest.raises(PhoneError, match="does not fit"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a long line of chat " * 3)] * 6)
    with pytest.raises(PhoneError, match="status"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a")], status=[(0.0, "lost")])
    with pytest.raises(PhoneError, match="status"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a")], status=[(1.0, "sent"), (0.5, "read")])
    with pytest.raises(PhoneError, match="mine"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a", mine=False)], status=[(0.0, "sent")])
    with pytest.raises(PhoneError, match="typing"):
        ink_phone.phone(cv, cv.comp, "Boss", [Bubble("a")], typing=(2.0, 1.0))


def test_the_phone_is_a_registered_ink_prop():
    entry = registry.get("prop", "ink-phone")
    assert entry.style == "ink"


def test_the_phone_shot_holds_the_phone_over_the_desk_with_the_signature_cactus():
    cv = canvas()
    ink_phone.phone_shot(cv, cv.comp, "Boss", [Bubble("hi")])
    ids = [g.get("id") for g in tree(cv).iter("group")]
    assert any(i.startswith("sig-cactus") for i in ids)
    assert "Boss" in texts(cv)
    assert registry.get("location", "ink-phone-shot").style == "ink"


@pytest.mark.parametrize("at", [True, math.nan, math.inf, -1.0])
def test_a_time_is_a_finite_number_of_seconds_from_zero(at):
    """A bool, NaN or infinity is not a time: each would place a bubble, a status or the typing dots nowhere."""
    for chat in (
        dict(bubbles=[Bubble("hi", at=at)]),
        dict(bubbles=[Bubble("hi")], status=[(at, "delivered")]),
        dict(bubbles=[Bubble("hi")], typing=(at, 9.0)),
    ):
        cv = canvas()
        with pytest.raises(PhoneError, match="a time is seconds into the take, from 0"):
            ink_phone.phone(cv, cv.comp, "Boss", **chat)
