"""An invented weather map and an invented message thread: they letter only what they are given, draw no real place or
app, and refuse what they could not show."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_forecast, flat_counter, registry
from srstudio.canvas import Signature
from srstudio.collage_forecast import ForecastError, Message, thread, weather_map
from srstudio.errors import SrstudioError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    cv.font_asset = "font"
    return cv


def letters(cv: Canvas) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [e.get("text") or (e.text or "") for e in root.iter() if e.tag.endswith("text")]


THREAD = dict(x=190.0, y=800.0, w=700.0, h=1040.0, contact="DON'T", clock=((0.0, "8:59"), (5.0, "9:00")))


def test_both_are_registered_collage_props():
    names = {(p.kind, p.name) for p in registry.entries("prop")}
    assert {("prop", "collage-weather-map"), ("prop", "collage-thread")} <= names


def test_the_error_is_the_librarys():
    assert issubclass(ForecastError, SrstudioError) and issubclass(ForecastError, ValueError)


def test_a_map_letters_only_its_arrow_and_its_clock():
    cv = canvas()
    weather_map(cv, cv.comp, 600, 600, 450, 600, arrow="EXES", clock=("8:59", (3.0, 7.0)))
    assert sorted(letters(cv)) == ["8:59", "EXES"]


def test_a_map_with_nothing_to_say_letters_nothing():
    cv = canvas()
    weather_map(cv, cv.comp, 600, 600, 450, 600)
    assert letters(cv) == []


def test_the_arrow_slides_on_the_times_it_is_given():
    cv = canvas()
    weather_map(cv, cv.comp, 600, 600, 450, 600, arrow="EXES", slide=(0.0, 1.5))
    still = canvas()
    weather_map(still, still.comp, 600, 600, 450, 600, arrow="EXES")
    moved = cv.scene.to_bytes()
    assert moved != still.scene.to_bytes() and b"<key " in moved and b"<key " not in still.scene.to_bytes()


def test_a_bare_arrow_letters_nothing_but_is_still_drawn():
    bare, none = canvas(), canvas()
    weather_map(bare, bare.comp, 600, 600, 450, 600, arrow="")
    weather_map(none, none.comp, 600, 600, 450, 600)
    assert letters(bare) == [] and len(bare.scene.to_bytes()) > len(none.scene.to_bytes())


def test_a_short_bubble_keeps_its_word_on_one_row_on_a_small_phone():
    cv = canvas()
    thread(cv, cv.comp, **{**THREAD, "w": 372.0, "h": 640.0}, messages=(Message("HEY", 1.0),))
    root = ET.fromstring(cv.scene.to_bytes())
    box = next(e for e in root.iter() if e.tag.endswith("text") and e.get("text") == "HEY")
    assert int(box.get("width")) >= 3 * 0.62 * float(box.get("size"))


@pytest.mark.parametrize(
    "args, kw, match",
    [
        ((600, 600, 40, 600), {}, "wide"),
        ((600, 600, 450, 0), {}, "tall"),
        ((600, 600, math.nan, 600), {}, "wide"),
        ((600, 600, 450, 600), dict(arrow="exes"), "capitals"),
        ((600, 600, 450, 600), dict(arrow="A VERY LONG COLD FRONT INDEED"), "fit"),
        ((600, 600, 450, 600), dict(slide=(2.0, 1.0)), "slide"),
        ((600, 600, 450, 600), dict(clock=("8:59", (5.0, 1.0))), "clock"),
    ],
)
def test_a_map_it_could_not_draw_is_refused(args, kw, match):
    cv = canvas()
    with pytest.raises(ForecastError, match=match):
        weather_map(cv, cv.comp, *args, **kw)


def test_a_thread_letters_the_clock_the_contact_the_messages_and_the_call():
    cv = canvas()
    thread(cv, cv.comp, **THREAD, call="PRIYA", messages=(Message("HEY", 5.0), Message("HEY", 8.0, mine=True)))
    assert sorted(letters(cv)) == sorted(["8:59", "9:00", "DON'T", "PRIYA", "HEY", "HEY"])


def test_a_thread_names_no_app_and_prints_no_number_or_address():
    cv = canvas()
    thread(cv, cv.comp, **THREAD)
    assert not [t for t in letters(cv) if "@" in t or "." in t or t.replace(":", "").isdigit() and ":" not in t]


def test_a_message_waits_for_its_time():
    cv = canvas()
    thread(cv, cv.comp, **THREAD, messages=(Message("HEY", 5.0),))
    assert "opacity" in cv.scene.to_bytes().decode()


def test_two_times_of_a_clock_never_show_together():
    spans = collage_forecast._clock_spans(((0.0, "8:59"), (5.0, "9:00")))
    assert spans == [("8:59", 0.0, 5.0), ("9:00", 5.0, collage_forecast.FOREVER)]


@pytest.mark.parametrize(
    "kw, match",
    [
        (dict(w=60.0), "wide"),
        (dict(h=float("inf")), "tall"),
        (dict(contact="don't"), "capitals"),
        (dict(contact=""), "contact"),
        (dict(clock=()), "clock"),
        (dict(clock=((5.0, "9:00"), (1.0, "8:59"))), "clock"),
        (dict(call="priya"), "capitals"),
        (dict(messages=(Message("hey", 1.0),)), "capitals"),
        (dict(messages=(Message("", 1.0),)), "message"),
        (dict(messages=(Message("HEY", -1.0),)), "message"),
        (dict(messages=(Message("HEY", 5.0), Message("HEY", 1.0))), "order"),
        (dict(w=240.0, h=420.0), "legib"),
        (dict(messages=(Message("A VERY LONG MESSAGE " * 12, 1.0),)), "fit"),
    ],
)
def test_a_thread_it_could_not_show_is_refused(kw, match):
    cv = canvas()
    with pytest.raises(ForecastError, match=match):
        thread(cv, cv.comp, **{**THREAD, **kw})
