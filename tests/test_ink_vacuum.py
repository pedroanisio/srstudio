"""The Ink robot vacuum: a talking disc whose ring chases while it speaks, that rolls, stops or sits still, shows a
word on its display, and its floor map, whose rooms are traced and can be relabelled; plus the refusals."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_vacuum, registry, shared_counter
from srstudio.canvas import Signature
from srstudio.ink_vacuum import Room, VacuumError
from srstudio.timeline import Take


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def take(actor: str = "vacuum", duration: float = 2.0, shot: str = "vacuum") -> Take:
    return Take("01", actor, shot, "Your free trial ended.", 0.0, duration)


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


def animated(cv: Canvas, prop: str):
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == prop
    ]


def ids(cv: Canvas):
    return [g.get("id") or "" for g in tree(cv).iter()]


def test_the_parts_are_registered_in_the_ink_style():
    entries = {e.name: e for e in registry.entries()}
    for kind, name in (("character", "talking-vacuum"), ("location", "ink-vacuum-shot"), ("graphic", "ink-floor-map")):
        assert entries[name].kind == kind and entries[name].style == "ink"


def test_the_vacuum_chases_its_ring_and_shows_voice_marks_only_when_it_speaks():
    talking, silent = canvas(), canvas()
    ink_vacuum.vacuum(talking, talking.comp, take(), 300, 600)
    ink_vacuum.vacuum(silent, silent.comp, take("human"), 300, 600)
    assert animated(silent, "opacity") == []
    fades = animated(talking, "opacity")
    assert len(fades) == ink_vacuum.RING_LEDS + 1  # each light of the ring, and the voice marks
    assert all(k[0] == (0.0, 1.0) and k[-1][0] < 2.0 for k in fades[: ink_vacuum.RING_LEDS])


@pytest.mark.parametrize("state", ["still", "roll", "stop"])
def test_the_vacuum_rolls_stops_or_sits_still(state):
    cv = canvas()
    ink_vacuum.vacuum(cv, cv.comp, take("human"), 300, 600, state=state)
    xs = animated(cv, "x")
    if state == "still":
        assert xs == []
    elif state == "roll":
        assert xs[0][0] == (0.0, 300.0) and xs[0][-1][1] > 300  # it rolls off to the right through the take
    else:
        assert xs[0][0][1] < 300 and xs[0][-1] == (pytest.approx(xs[0][-1][0]), 300.0)  # it rolls in and brakes


def test_the_display_shows_a_short_word_and_the_body_carries_the_signature():
    cv = canvas()
    ink_vacuum.vacuum(cv, cv.comp, take(), 300, 600, display="PRO")
    assert "PRO" in texts(cv)
    assert any(i.startswith("sig-") for i in ids(cv))


@pytest.mark.parametrize(
    ("kw", "match"),
    [(dict(state="fly"), "state"), (dict(display="PREMIUM PLAN"), "display"), (dict(display=""), "display")],
)
def test_the_vacuum_refuses_what_it_cannot_do(kw, match):
    cv = canvas()
    with pytest.raises(VacuumError, match=match):
        ink_vacuum.vacuum(cv, cv.comp, take(), 300, 600, **kw)


def test_the_vacuum_shot_puts_it_on_the_floor_by_the_wall():
    cv = canvas()
    ink_vacuum.vacuum_shot(cv, cv.comp, take(), close=False)
    near = canvas()
    ink_vacuum.vacuum_shot(near, near.comp, take(), close=True, display="$")
    assert "$" in texts(near)
    scale = [float(g.get("scaleX")) for g in tree(cv).iter("group") if g.get("scaleX")]
    close = [float(g.get("scaleX")) for g in tree(near).iter("group") if g.get("scaleX")]
    assert max(close) > max(scale)


def test_the_floor_map_traces_the_route_and_labels_every_room():
    cv = canvas()
    ink_vacuum.floor_map(cv, cv.comp, take(duration=3.0), trace=(0.2, 1.6))
    shown = texts(cv)
    assert {r.label for r in ink_vacuum.PLAN} <= set(shown)
    dots = [k for k in animated(cv, "opacity") if len(k) == 2 and k[0] == (0.0, 0.0)]
    assert len(dots) == ink_vacuum.TRACE_DOTS
    times = [k[1][0] for k in dots]
    assert times == sorted(times) and times[0] == pytest.approx(0.2) and times[-1] == pytest.approx(1.6)


def test_the_floor_map_relabels_a_room_at_its_moment():
    cv = canvas()
    ink_vacuum.floor_map(cv, cv.comp, take(duration=3.0), relabel=("CLOSET", "BEDROOM 2", 1.0))
    shown = texts(cv)
    assert "CLOSET" in shown and "BEDROOM 2" in shown
    fades = animated(cv, "opacity")
    assert [(0.0, 1.0), (1.0, 0.0)] in fades and [(0.0, 0.0), (1.0, 1.0)] in fades


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(relabel=("GARAGE", "BEDROOM 2", 1.0)), "no room"),
        (dict(relabel=("CLOSET", "THE MASTER SUITE", 1.0)), "label"),
        (dict(relabel=("CLOSET", "BEDROOM 2", 9.0)), "within the take"),
        (dict(trace=(1.5, 0.5)), "trace"),
        (dict(trace=(0.5, 9.0)), "trace"),
        (dict(rooms=()), "at least one room"),
        (dict(rooms=(Room("A", 0, 0, 10, 10), Room("A", 20, 0, 10, 10))), "twice"),
    ],
)
def test_the_floor_map_refuses_what_it_cannot_show(kw, match):
    cv = canvas()
    with pytest.raises(VacuumError, match=match):
        ink_vacuum.floor_map(cv, cv.comp, take(duration=3.0), **kw)
