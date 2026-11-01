"""news-corridor-map: a corridor from above, two dots that step in sync, and a count of how many times."""

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


UP = ((2.0, 240.0, 460.0), (3.0, 460.0, 460.0), (4.0, 240.0, 460.0))
DOWN = ((2.0, 240.0, 240.0), (3.0, 460.0, 240.0), (4.0, 240.0, 240.0))


def corridor(cv: Canvas, **over) -> None:
    kwargs = dict(
        title="THE CORRIDOR",
        counter="SIDESTEPS",
        one=UP,
        other=DOWN,
        counts=((2.0, "1"), (3.0, "2")),
        start=2.0,
        end=6.0,
        measure=measure,
    )
    news_inked.corridor_map(cv, cv.comp, **{**kwargs, **over})


def test_the_map_is_up_for_its_window():
    cv = canvas()
    corridor(cv)
    group = nodes(cv)["news-corridor-map"]
    assert (group.get("start"), group.get("end")) == ("2", "6")


def test_both_men_are_drawn_and_move():
    cv = canvas()
    corridor(cv)
    found = nodes(cv)
    for name in ("news-corridor-map-one", "news-corridor-map-other"):
        assert len(list(found[name].iter())) > 1


def test_a_step_is_quick_and_then_holds():
    """Each move takes the same short time, so two men who step together are seen to."""
    keys = news_inked.corridor_keys(UP)
    assert keys[0] == (2.0, 240.0, 460.0)
    assert keys[1:3] == [(3.0, 240.0, 460.0), (pytest.approx(3.0 + news_inked.CORRIDOR_STEP), 460.0, 460.0)]


def test_each_count_holds_until_the_next():
    cv = canvas()
    corridor(cv)
    first, second = nodes(cv)["news-corridor-map-count-0"], nodes(cv)["news-corridor-map-count-1"]
    assert (first.get("start"), first.get("end")) == ("2", "3")
    assert (second.get("start"), second.get("end")) == ("3", "6")


def test_a_second_window_takes_its_own_ids():
    cv = canvas()
    corridor(cv)
    corridor(
        cv,
        start=7.0,
        end=11.0,
        one=((7.0, 240.0, 460.0),),
        other=((7.0, 460.0, 240.0),),
        counts=((7.0, "3"),),
        id="news-corridor-map-2",
    )
    assert "news-corridor-map-2-one" in nodes(cv)


@pytest.mark.parametrize(
    "over",
    [
        {"one": ()},
        {"other": ()},
        {"one": ((1.0, 240.0, 460.0),)},
        {"one": ((2.0, 240.0, 460.0), (2.0, 300.0, 460.0))},
        {"one": ((2.0, 240.0, 460.0), (5.95, 300.0, 460.0))},
        {"one": ((2.0, 40.0, 460.0),)},
        {"other": ((2.0, 240.0, 900.0),)},
        {"counts": ()},
        {"counts": ((5.0, "1"),)},
        {"title": "W" * 80},
        {"counter": "W" * 80},
    ],
)
def test_a_map_that_cannot_be_read_stops_the_build(over):
    with pytest.raises(news_kit.NewsKitError):
        corridor(canvas(), **over)


def test_a_span_that_is_not_one_stops_the_build():
    with pytest.raises(news_kit.NewsKitError):
        corridor(canvas(), start=5.0, end=5.0)


def test_the_part_is_registered_and_starts_proposed():
    versions = parts.get("news-corridor-map").versions
    assert [(v.number, v.status) for v in versions] == [(1, "proposed")]


def test_the_floor_dashes_stay_on_the_floor():
    top, foot = news_inked.CORRIDOR_TOP, news_inked.CORRIDOR_FOOT
    dashes = news_inked.corridor_dashes(top, foot)
    assert len(dashes) >= 4
    assert all(top < y and y + news_inked.CORRIDOR_DASH < foot for y in dashes)


def test_the_map_covers_the_banners_word():
    cv = canvas()
    corridor(cv)
    assert "news-corridor-map-rest" in nodes(cv)
