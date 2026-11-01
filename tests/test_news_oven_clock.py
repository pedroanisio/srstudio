"""news-oven-clock: an unbranded stove whose digits never change while the tag on them does."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, news_inked, news_kit, parts


def measure(text: str, size: float) -> float:
    return len(text) * size * 0.5


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette())


def nodes(cv: Canvas) -> dict:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty").decode())
    return {node.get("id"): node for node in root.iter() if node.get("id")}


def oven(cv: Canvas, **over) -> None:
    kwargs = dict(
        label="GUS'S OVEN",
        time="7:42",
        wrong="1 HOUR OFF",
        right="CORRECT",
        start=2.0,
        end=8.0,
        measure=measure,
        right_at=5.0,
    )
    news_inked.oven_clock(cv, cv.comp, **{**kwargs, **over})


def test_the_clock_is_up_for_its_window():
    cv = canvas()
    oven(cv)
    group = nodes(cv)["news-oven-clock"]
    assert (group.get("start"), group.get("end")) == ("2", "8")


def test_the_tag_turns_at_the_instant_it_is_told_and_the_digits_are_outside_it():
    cv = canvas()
    oven(cv)
    drawn = nodes(cv)
    assert (drawn["news-oven-clock-wrong"].get("end"), drawn["news-oven-clock-right"].get("start")) == ("5", "5")
    digits = drawn["news-oven-clock-digits"]
    assert digits.get("start") in (None, "2") and digits.get("end") in (None, "8")


def test_a_clock_with_no_turn_stays_wrong():
    cv = canvas()
    oven(cv, right_at=None)
    drawn = nodes(cv)
    assert "news-oven-clock-right" not in drawn
    assert drawn["news-oven-clock-wrong"].get("end") == "8"


@pytest.mark.parametrize(("digit", "lit"), [("8", 7), ("1", 2), ("7", 3), ("0", 6), ("4", 4), ("2", 5)])
def test_a_digit_lights_the_segments_it_is_made_of(digit, lit):
    assert len(news_inked.OVEN_SEGMENTS[digit]) == lit


def test_every_segment_of_every_digit_is_drawn_lit_or_dark():
    cv = canvas()
    fills = []
    real = cv.rect

    def spy(parent, x, y, w, h, fill=None, *rest, **kw):
        fills.append(fill)
        return real(parent, x, y, w, h, fill, *rest, **kw)

    cv.rect = spy
    oven(cv, time="7:42")
    assert fills.count(news_inked.OVEN_LIT) == 3 + 4 + 5 + 2  # the 7, the 4, the 2 and the colon's two dots
    assert fills.count(news_inked.OVEN_DARK) == 3 * 7 - 3 - 4 - 5


def test_the_part_is_a_registered_graphic_that_needs_no_face():
    part = parts.get("news-oven-clock")
    assert part.kind == "graphic"


@pytest.mark.parametrize(
    "over",
    [
        {"start": 8.0},
        {"right_at": 1.0},
        {"right_at": 8.0},
        {"time": "742"},
        {"time": "7:4"},
        {"time": "13:61"},
        {"time": "a:bc"},
        {"label": ""},
        {"wrong": ""},
        {"right": "RIGHT " * 12},
        {"label": "OVEN " * 12},
    ],
)
def test_a_clock_that_cannot_be_read_or_runs_off_its_window_is_refused(over):
    with pytest.raises(news_kit.NewsKitError):
        oven(canvas(), **over)


def test_engagement_bait_stays_off_the_clock():
    with pytest.raises(news_kit.NewsKitError):
        oven(canvas(), right="FOLLOW FOR MORE")
