"""One bar: a chair to stand on, the arm that holds the phone up, the upload's chip and a sandwich on a broom."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter
from srstudio.readings import held
from srstudio.toon import ToonDataError
from srstudio.toon_signal import BAR_ON, BARS, NO_SIGNAL, broom, climb_chair, raised_phone, table_legs, upload_chip


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=30.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def root(cv: Canvas):
    return cv.group(cv.comp, "root")


def doc(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def measure(text: str, size: float) -> float:
    return len(text) * size * 0.6


def timed(cv: Canvas, name: str) -> list[tuple[float, float]]:
    return [
        (float(g.get("start")), float(g.get("end")))
        for g in doc(cv).iter("group")
        if (g.get("id") or "").startswith(name)
    ]


def test_the_chair_draws_at_its_feet():
    cv = canvas()
    climb_chair(cv, root(cv), (210.0, 806.0))
    shapes = [e for e in doc(cv).iter() if e.get("fill")]
    assert len(shapes) >= 5


def test_the_legs_stand_clear_of_the_signature_code():
    cv = canvas()
    table_legs(cv, root(cv))
    shapes = [e for e in doc(cv).iter() if e.get("fill")]
    assert len(shapes) >= 5


def test_no_signal_is_drawn_when_no_bar_is_lit():
    cv = canvas()
    raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((0.0, 0),), 0.0, 5.0)
    state = next(g for g in doc(cv).iter("group") if g.get("id") == "signal-0")
    assert sum(1 for e in state.iter() if e.get("stroke") == NO_SIGNAL) == 2


def test_a_forearm_runs_down():
    cv = canvas()
    with pytest.raises(ToonDataError, match="forearm"):
        raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((0.0, 1),), 0.0, 5.0, down=0.0)


@pytest.mark.parametrize("at", [(-400.0, 806.0), (210.0, 1400.0), (210.0, 120.0)])
def test_a_chair_stands_in_the_frame(at):
    cv = canvas()
    with pytest.raises(ToonDataError, match="chair"):
        climb_chair(cv, root(cv), at)


def test_a_chair_keeps_off_the_signature():
    cv = canvas()
    with pytest.raises(ToonDataError, match="signature"):
        climb_chair(cv, root(cv), (450.0, 900.0))


def test_each_bar_reading_has_its_own_span_to_the_end():
    cv = canvas()
    raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((0.0, 1), (10.0, 0)), 0.0, 20.0)
    assert timed(cv, "signal-") == [(0.0, 10.0), (10.0, 20.0)]


def test_the_lit_bars_are_the_count_read():
    cv = canvas()
    raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((0.0, 3),), 0.0, 5.0)
    state = next(g for g in doc(cv).iter("group") if g.get("id") == "signal-0")
    fills = [e.get("fill") for e in state.iter() if e.get("fill")]
    assert len(fills) == BARS and fills.count(BAR_ON) == 3


def test_a_phone_cannot_read_more_bars_than_it_has():
    cv = canvas()
    with pytest.raises(ToonDataError, match="bars"):
        raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((0.0, BARS + 1),), 0.0, 5.0)


def test_bar_readings_run_in_order_from_the_start():
    cv = canvas()
    with pytest.raises(ToonDataError, match="order"):
        raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((2.0, 1), (1.0, 0)), 2.0, 5.0)
    with pytest.raises(ToonDataError, match="first"):
        raised_phone(cv, root(cv), (120.0, 262.0), "#7fcf6b", "#4f9a46", ((1.0, 1),), 0.0, 5.0)


def test_a_phone_keeps_in_the_frame_and_off_the_marks():
    cv = canvas()
    with pytest.raises(ToonDataError, match="frame"):
        raised_phone(cv, root(cv), (120.0, 200.0), "#7fcf6b", "#4f9a46", ((0.0, 1),), 0.0, 5.0)
    with pytest.raises(ToonDataError, match="signature"):
        raised_phone(cv, root(cv), (530.0, 900.0), "#7fcf6b", "#4f9a46", ((0.0, 1),), 0.0, 5.0)


def test_the_chip_shows_each_reading_on_its_clock_with_its_share_of_the_bar():
    cv = canvas()
    readings = held(((0.0, "9%"), (3.0, "40%"), (6.0, "SENT")), 9.0)
    upload_chip(cv, root(cv), readings, (0.09, 0.4, 1.0), measure=measure, at=(420.0, 380.0))
    assert timed(cv, "upload-read-") == [(0.0, 3.0), (3.0, 6.0), (6.0, 9.0)]
    widths = [
        max(float(r.get("width")) for r in g.iter() if r.get("width"))
        for g in doc(cv).iter("group")
        if (g.get("id") or "").startswith("upload-bar-")
    ]
    assert widths[0] < widths[1] < widths[2]


def test_the_chip_has_one_share_per_reading():
    cv = canvas()
    with pytest.raises(ToonDataError, match="one share"):
        upload_chip(cv, root(cv), held(((0.0, "9%"),), 2.0), (0.1, 0.2), measure=measure)


@pytest.mark.parametrize("share", [-0.1, 1.5, float("nan")])
def test_a_share_is_between_nothing_and_all(share):
    cv = canvas()
    with pytest.raises(ToonDataError, match="share"):
        upload_chip(cv, root(cv), held(((0.0, "9%"),), 2.0), (share,), measure=measure)


def test_a_reading_must_fit_the_chip():
    cv = canvas()
    with pytest.raises(ToonDataError, match="wide"):
        upload_chip(cv, root(cv), held(((0.0, "A LONG READING INDEED"),), 2.0), (0.5,), measure=measure)


@pytest.mark.parametrize("at", [(296.0, 280.0), (540.0, 240.0), (20.0, 500.0)])
def test_the_chip_keeps_off_the_caption_the_marks_and_the_frame_edge(at):
    cv = canvas()
    with pytest.raises(ToonDataError, match="upload chip"):
        upload_chip(cv, root(cv), held(((0.0, "9%"),), 2.0), (0.09,), measure=measure, at=at)


def test_the_broom_goes_where_it_is_told():
    cv = canvas()
    stops = ((5.0, 300.0, 900.0), (5.6, 230.0, 500.0), (7.0, 230.0, 500.0), (7.5, 300.0, 900.0))
    broom(cv, root(cv), stops, 5.0, 8.0, 6.2)
    props = {a.get("property"): [float(k.get("value")) for k in a.iter("key")] for a in doc(cv).iter("animate")}
    assert props["x"][0] > props["x"][1] and props["y"][0] > props["y"][1]


def test_the_bite_swaps_the_whole_sandwich_for_the_bitten_one():
    cv = canvas()
    broom(cv, root(cv), ((5.0, 300.0, 900.0), (5.6, 230.0, 500.0)), 5.0, 8.0, 6.2)
    assert timed(cv, "sandwich-") == [(5.0, 6.2), (6.2, 8.0)]


def test_a_broom_moves_in_order_and_bites_while_it_is_up():
    cv = canvas()
    with pytest.raises(ToonDataError, match="order"):
        broom(cv, root(cv), ((6.0, 300.0, 900.0), (5.6, 230.0, 500.0)), 5.0, 8.0, 6.2)
    with pytest.raises(ToonDataError, match="bite"):
        broom(cv, root(cv), ((5.0, 300.0, 900.0), (5.6, 230.0, 500.0)), 5.0, 8.0, 9.0)
    with pytest.raises(ToonDataError, match="two"):
        broom(cv, root(cv), ((5.0, 300.0, 900.0),), 5.0, 8.0, 6.2)
    with pytest.raises(ToonDataError, match="clock"):
        broom(cv, root(cv), ((5.0, 300.0, 900.0), (5.6, 230.0, 500.0)), 8.0, 5.0, 6.2)
