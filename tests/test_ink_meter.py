"""The Ink parking meter: a talking pay station whose coin slot is taped over, whose display changes over the take
and whose lights chase only while it speaks; the kerb it stands on, with the doodle, a parked car and the tow truck
that takes it; and the parking app on a held phone, each row arriving and ticking in turn, a progress bar that
fills and five stars that light; plus the refusals."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_meter, registry, shared_counter
from srstudio.canvas import Signature
from srstudio.ink_meter import AppRow, MeterError
from srstudio.timeline import Take


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def take(actor: str = "meter", duration: float = 2.0, shot: str = "kerb", mood: str = "calm") -> Take:
    return Take("01", actor, shot, "Scan me.", 0.0, duration, mood=mood)


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


def test_the_parts_are_registered_in_the_ink_style():
    entries = {e.name: e for e in registry.entries()}
    for kind, name in (("character", "talking-meter"), ("location", "ink-kerb"), ("graphic", "ink-app-screen")):
        assert entries[name].kind == kind and entries[name].style == "ink"


def test_the_meter_chases_its_lights_and_shows_voice_marks_only_when_it_speaks():
    talking, silent = canvas(), canvas()
    ink_meter.meter(talking, talking.comp, take(), 500, 300)
    ink_meter.meter(silent, silent.comp, take("human"), 500, 300)
    assert animated(silent, "opacity") == []
    fades = animated(talking, "opacity")
    assert len(fades) == ink_meter.LIGHTS + 1  # each light over the display, and the voice marks
    assert all(k[0] == (0.0, 1.0) and k[-1][0] < 2.0 for k in fades[: ink_meter.LIGHTS])


def test_the_slot_is_taped_over_and_the_display_changes_on_cue():
    cv = canvas()
    ink_meter.meter(cv, cv.comp, take("human"), 500, 300, display=((0.0, "SCAN TO PAY"), (1.2, "THANK YOU")))
    assert {"SCAN TO PAY", "THANK YOU", ink_meter.TAPE_TEXT} <= set(texts(cv))
    assert [(0.0, 0.0), (1.2, 1.0)] in animated(cv, "opacity")  # the second reading shows from 1.2 s


def test_the_kerb_puts_the_doodle_the_meter_and_the_car_in_frame_and_a_tow_takes_the_car():
    still, towed = canvas(), canvas()
    ink_meter.kerb(still, still.comp, take("human", 3.0))
    ink_meter.kerb(towed, towed.comp, take("human", 3.0), tow=0.8)
    assert animated(still, "x") == [] and animated(still, "rotation") == []
    (rise,) = animated(towed, "rotation")  # the hook lifts the car's front
    assert rise[0] == (0.0, 0.0) and rise[1][0] == pytest.approx(0.8) and rise[-1][1] < 0
    (away,) = animated(towed, "x")  # then truck and car leave to the right
    assert away[0][0] == pytest.approx(0.8) and away[-1][1] > away[0][1] + 1080


def test_the_close_kerb_frames_the_meter_alone(monkeypatch):
    drawn = []
    monkeypatch.setattr(ink_meter, "human", lambda *a, **kw: drawn.append(a))
    wide, close = canvas(), canvas()
    ink_meter.kerb(wide, wide.comp, take())
    assert len(drawn) == 1  # the wide kerb has the doodle on the pavement
    ink_meter.kerb(close, close.comp, take(), close=True, display=((0.0, "2 HR MIN"),))
    assert "2 HR MIN" in texts(close) and len(drawn) == 1  # the close one is the meter alone


def test_the_app_screen_lays_out_its_rows_ticks_them_and_fills_its_bar_and_stars():
    cv = canvas()
    rows = (AppRow("A capital", at=0.2, tick=0.6), AppRow("A symbol", at=0.4, tick=0.9), AppRow("A memory", at=0.6))
    ink_meter.app_screen(cv, cv.comp, take("meter", 3.0), title="ParkPal", rows=rows, progress=(0.0, 1.5), stars=2.0)
    assert {"ParkPal", "A capital", "A symbol", "A memory"} <= set(texts(cv))
    fades = animated(cv, "opacity")
    assert [(0.0, 0.0), (0.2, 1.0)] in fades and [(0.0, 0.0), (0.6, 1.0)] in fades  # rows arrive in turn
    assert sum(1 for k in fades if k == [(0.0, 0.0), (0.9, 1.0)]) == 1  # the second tick, once
    (bar,) = animated(cv, "scaleX")
    assert bar[0] == (0.0, 0.0) and bar[-1] == (1.5, 1.0)
    lit = [k for k in fades if k[-1][0] >= 2.0 and k[0] == (0.0, 0.0)]
    assert len(lit) == ink_meter.STARS  # five stars light, one after another, from 2.0 s
    assert [k[-1][0] for k in lit] == sorted(k[-1][0] for k in lit)


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=()), "display"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.5, "LATE"),)), "from 0"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.0, "A"), (0.0, "B"))), "rising"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.0, "X" * 20),)), "characters"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.0, "OK"), (9.0, "NO"))), "within"),
        (lambda cv: ink_meter.kerb(cv, cv.comp, take(), tow=-1.0), "tow"),
        (lambda cv: ink_meter.kerb(cv, cv.comp, take(), tow=5.0), "tow"),
        (lambda cv: ink_meter.kerb(cv, cv.comp, take(), close=True, tow=1.0), "close"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="", rows=()), "title"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x"),) * 9), "rows"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow(""),)), "row"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", at=3.0),)), "within"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", 0.5, 0.2),)), "tick"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(), progress=(1.0, 0.5)), "progress"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(), stars=7.0), "stars"),
    ],
)
def test_the_meter_the_kerb_and_the_app_refuse_what_they_cannot_show(call, match):
    with pytest.raises(MeterError, match=match):
        call(canvas())
