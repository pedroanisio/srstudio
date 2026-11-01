"""A car at night: the timer reads from the second it is given, no reading stays too briefly to read, and the chip
refuses what cannot be read or would sit on a mark."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, toon_night
from srstudio.toon import ToonDataError
from srstudio.toon_night import LEAST, call_chip, night_cabin, night_dash, reading, ticks


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=30.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def texts(cv: Canvas) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [a.get("text", "") for a in root.iter("text")]


def test_a_timer_reads_minutes_and_seconds():
    assert reading(862) == "14:22"
    assert reading(0) == "00:00"


@pytest.mark.parametrize("bad", [-1, 6000, 1.5, True])
def test_a_timer_refuses_what_it_cannot_show(bad):
    with pytest.raises(ToonDataError):
        reading(bad)


def test_the_timer_counts_from_the_reading_it_is_given():
    rows = ticks(0.0, 17.0, (14.9, 862))
    text = dict((round(a, 3), t) for a, _, t in rows)
    assert text[14.9] == "14:22"
    assert rows[0][2] == "14:07"
    assert rows[-1][2] == "14:23"


def test_no_reading_stays_too_briefly_to_read():
    for start, end in ((0.0, 15.05), (3.3, 9.05), (0.2, 1.1), (7.95, 12.1)):
        rows = ticks(start, end, (14.9, 862))
        assert rows[0][0] == start and rows[-1][1] == end
        assert all(b - a >= LEAST for a, b, _ in rows), rows


def test_readings_touch_with_no_gap():
    rows = ticks(2.0, 9.0, (14.9, 862))
    assert all(a[1] == b[0] for a, b in zip(rows, rows[1:], strict=False))


@pytest.mark.parametrize(
    ("start", "end", "reads"),
    [(5.0, 4.0, (0.0, 10)), (-1.0, 4.0, (0.0, 10)), (0.0, 0.5, (0.0, 10)), (0.0, 4.0, (20.0, 3))],
)
def test_a_timer_refuses_a_window_it_cannot_fill(start, end, reads):
    with pytest.raises(ToonDataError):
        ticks(start, end, reads)


def chip(**kw) -> Canvas:
    cv = canvas()
    root = cv.group(cv.comp, "root")
    args = {"start": 0.0, "end": 16.0, "measure": measure, "reads": (14.9, 862)}
    args.update(kw)
    call_chip(cv, root, args.pop("name", "Dana"), args.pop("reads"), args.pop("start"), args.pop("end"), **args)
    return cv


def test_the_chip_names_the_call_and_reaches_its_reading():
    words = texts(chip())
    assert "CALL: DANA" in words and "14:22" in words and "14:07" in words


def test_the_chip_lights_from_its_second_and_stays_lit():
    dim = chip()
    lit = chip(lit_from=14.4)
    assert "#eafff4" not in dim.scene.to_bytes(layout="pretty").decode()
    assert "#eafff4" in lit.scene.to_bytes(layout="pretty").decode()


def test_lighting_up_splits_no_text_into_a_piece_too_brief_to_read():
    spans = []
    for g in ET.fromstring(chip(lit_from=14.4, start=13.0, end=16.0).scene.to_bytes(layout="pretty")).iter("group"):
        if g.get("end") is not None and g.find("layer") is not None:
            spans.append(float(g.get("end")) - float(g.get("start")))
    assert spans and min(spans) >= LEAST


@pytest.mark.parametrize(
    "kw",
    [
        {"name": ""},
        {"name": "A much too long name for a dashboard readout to hold"},
        {"at": (296.0, 280.0)},
        {"at": (560.0, 830.0)},
        {"scale": 3.0},
        {"lit_from": -1.0},
    ],
)
def test_the_chip_refuses_what_cannot_be_read_or_sits_on_a_mark(kw):
    with pytest.raises(ToonDataError):
        chip(**kw)


def test_the_set_draws_with_no_error_and_no_lettering():
    cv = canvas()
    root = cv.group(cv.comp, "root")
    night_cabin(cv, root)
    night_dash(cv, root)
    night_dash(cv, root, close=True)
    assert not [t for t in texts(cv) if t != toon_night.__name__ and any(c.isalpha() for c in t) and "SR" not in t]
