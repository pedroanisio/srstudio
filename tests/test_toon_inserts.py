"""The small Toon parts: each is registered, each refuses what it cannot draw, and nothing shows before its time."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, specimens, toon_inserts
from srstudio.toon import ToonDataError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(cv: Canvas, name: str):
    return next(n for n in tree(cv).iter("group") if n.get("id") == name)


def texts(cv: Canvas) -> list[str]:
    return [n.get("text", "") for n in tree(cv).iter() if n.tag == "text"]


def test_the_drops_fall_on_the_eye_while_the_bottle_is_there():
    specimens.load_parts()
    assert registry.get("prop", "toon-eye-drops").builder is toon_inserts.eye_drops
    cv = canvas()
    toon_inserts.eye_drops(cv, cv.comp, start=1.0, squeezes=(1.5, 2.0), leave=3.0, id="bottle")
    bottle = group(cv, "bottle")
    assert (float(bottle.get("start")), float(bottle.get("end"))) == (1.0, 3.0)
    assert [float(g.get("start")) for g in bottle.iter("group") if g is not bottle] == [1.5, 2.0]


@pytest.mark.parametrize(
    "bad",
    [
        {"squeezes": ()},
        {"start": 1.0, "squeezes": (0.5,)},
        {"squeezes": (1.2, 0.6)},
        {"squeezes": (0.6,), "leave": 0.7},
        {"start": -1.0},
        {"scale": 0.0},
    ],
)
def test_drops_refuse_a_time_they_cannot_keep(bad):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_inserts.eye_drops(cv, cv.comp, **bad)


def test_the_glass_stands_on_the_counter_and_refuses_to_stand_above_nothing():
    specimens.load_parts()
    assert registry.get("prop", "toon-reception-glass").builder is toon_inserts.reception_glass
    cv = canvas()
    toon_inserts.reception_glass(cv, cv.comp)
    assert sum(1 for _ in tree(cv).iter("shape")) > 6
    for bad in ({"left": 300.0, "right": 100.0}, {"top": 900.0}, {"top": float("nan")}):
        with pytest.raises(ToonDataError):
            toon_inserts.reception_glass(cv, cv.comp, **bad)


def test_a_voice_note_reads_on_a_phone_and_fills_as_it_plays():
    specimens.load_parts()
    assert registry.get("graphic", "toon-voice-note-bar").builder is toon_inserts.voice_note_bar
    cv = canvas()
    stops = ((0.0, "0:04", 0.01), (5.0, "4:10", 0.35), (9.0, "11:44", 0.99))
    toon_inserts.voice_note_bar(cv, cv.comp, stops, end=10.0, doubled=(1.0, 8.0))
    sizes = [int(n.get("size")) for n in tree(cv).iter() if n.get("size")]
    assert sizes and min(sizes) >= toon_inserts.READ_SIZE
    fill = next(a for a in tree(cv).iter("animate") if a.get("property") == "scaleX")
    assert [float(k.get("value")) for k in fill] == [0.01, 0.35, 0.99]


@pytest.mark.parametrize(
    "bad",
    [
        {"stops": ()},
        {"stops": ((1.0, "0:04", 0.0),)},
        {"stops": ((0.0, "0:04", 0.5), (1.0, "0:05", 0.1))},
        {"stops": ((0.0, "0:04", 1.5),)},
        {"stops": ((0.0, "0:04", 0.1),), "end": 0.0},
        {"doubled": (3.0, 1.0)},
    ],
)
def test_a_voice_note_refuses_stops_it_cannot_show(bad):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_inserts.voice_note_bar(cv, cv.comp, **bad)


def test_a_gull_turns_inside_its_time_and_ends_with_its_eye_on_you():
    specimens.load_parts()
    assert registry.get("prop", "toon-gull-stare").builder is toon_inserts.gull_stare
    cv = canvas()
    toon_inserts.gull_stare(cv, cv.comp, turn=1.0, seconds=2.0, end=5.0)
    slides = [a for a in tree(cv).iter("animate") if a.get("property") == "x"]
    assert len(slides) == 2
    assert all(float(a[0].get("time")) == 1.0 and float(a[-1].get("time")) == 3.0 for a in slides)
    assert all(float(a[-1].get("value")) > float(a[0].get("value")) for a in slides)  # it comes round, never back


@pytest.mark.parametrize(
    "bad", [{"turn": 4.0, "seconds": 2.0, "end": 5.0}, {"seconds": 0.0}, {"turn": -1.0}, {"scale": 0.0}]
)
def test_a_gull_refuses_a_turn_it_has_no_time_for(bad):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_inserts.gull_stare(cv, cv.comp, **bad)
