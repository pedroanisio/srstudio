"""Moving a node to the music (ADR 0090): a body that rises on the beat, a lean, and a swap on the grid."""

from __future__ import annotations

from xml.etree import ElementTree

import numpy as np
import pytest
from sr_core.scene import Scene

from srstudio import Canvas, on_beat
from srstudio.music import Groove, MusicError

GRID = Groove(bpm=120.0, offset=1.0)  # a beat every 0.5 s, a bar opening at 1.0, 3.0, 5.0


@pytest.fixture
def cv() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10, seed=1)
    return Canvas(scene, font_asset=None)


def keys(cv, node, prop: str) -> list[tuple[float, float]]:
    tree = ElementTree.fromstring(cv.scene.to_bytes(layout="pretty"))
    group = next(e for e in tree.iter() if e.attrib.get("id") == node)
    animate = next(c for c in group if c.tag.endswith("animate") and c.attrib["property"] == prop)
    return [(float(k.attrib["time"]), float(k.attrib["value"])) for k in animate]


def test_a_grid_gives_its_beats_in_seconds_on_either_side_of_its_offset():
    assert GRID.between(0.2, 2.0) == pytest.approx([0.5, 1.0, 1.5])
    assert GRID.between(1.0, 2.0, every=0.5) == pytest.approx([1.0, 1.25, 1.5, 1.75])
    assert GRID.between(1.1, 1.2) == []
    with pytest.raises(MusicError):
        GRID.between(1.0, 2.0, every=0)
    with pytest.raises(MusicError):
        GRID.between(2.0, 1.0)


def test_a_grid_knows_the_beat_that_opens_a_bar():
    assert GRID.opens_bar(1.0) and GRID.opens_bar(3.0) and GRID.opens_bar(5.0)
    assert not GRID.opens_bar(1.5) and not GRID.opens_bar(2.0)
    assert GRID.opens_bar(GRID.offset - GRID.bar)


def test_a_body_rises_on_every_beat_settles_between_and_rises_more_on_the_bar(cv):
    node = cv.group(cv.comp, "body")
    on_beat.ride(cv, node, GRID, 1.0, 3.2, 7.0, bar_hit=1.5)
    expected = [(1.0, -10.5), (1.25, 7.0), (1.5, -7.0), (1.75, 7.0), (2.0, -7.0), (2.25, 7.0), (2.5, -7.0), (2.75, 7.0),
                (3.0, -10.5)]  # fmt: skip
    assert np.ravel(keys(cv, "body", "y")) == pytest.approx(np.ravel(expected))


def test_a_lean_swings_from_beat_to_beat(cv):
    node = cv.group(cv.comp, "friend")
    on_beat.sway(cv, node, GRID, 1.0, 2.6, 2.0, -3.0)
    assert np.ravel(keys(cv, "friend", "rotation")) == pytest.approx([1.0, 2.0, 1.5, -3.0, 2.0, 2.0, 2.5, -3.0])


def test_a_span_with_no_beat_in_it_is_refused(cv):
    node = cv.group(cv.comp, "body")
    with pytest.raises(MusicError, match="no beat"):
        on_beat.ride(cv, node, GRID, 1.1, 1.2, 7.0)
    with pytest.raises(MusicError, match="no beat"):
        on_beat.sway(cv, node, GRID, 1.1, 1.2, 2.0, -2.0)


@pytest.mark.parametrize("bad", [dict(height=0.0), dict(height=-1.0), dict(height=1.0, bar_hit=0.0)])
def test_a_ride_that_cannot_move_is_refused(cv, bad):
    node = cv.group(cv.comp, "body")
    with pytest.raises(MusicError):
        on_beat.ride(cv, node, GRID, 1.0, 2.0, **bad)


def test_two_states_swap_on_the_grid_and_cover_the_span():
    spans = on_beat.alternate(GRID, 0.9, 2.1, every=1.0)
    assert np.ravel(spans[True]) == pytest.approx([0.9, 1.0, 1.5, 2.0])
    assert np.ravel(spans[False]) == pytest.approx([1.0, 1.5, 2.0, 2.1])
    flipped = on_beat.alternate(GRID, 0.9, 2.1, every=1.0, first=False)
    assert flipped[True] == spans[False]


def test_a_ride_refuses_a_span_with_only_a_half_beat_in_it(cv):
    with pytest.raises(MusicError):
        on_beat.ride(cv, cv.group(cv.comp, "body"), GRID, 1.2, 1.3, 10.0)


def test_a_ride_and_a_lean_move_about_where_the_node_stands(cv):
    on_beat.ride(cv, cv.group(cv.comp, "body", y=300.0), GRID, 1.0, 2.0, 10.0)
    assert [y for _, y in keys(cv, "body", "y")] == pytest.approx([290.0, 310.0, 290.0, 310.0])
    on_beat.sway(cv, cv.group(cv.comp, "friend", rotation=5.0), GRID, 1.0, 2.0, -2.0, 2.0)
    assert [r for _, r in keys(cv, "friend", "rotation")] == pytest.approx([3.0, 7.0])


def test_swapped_states_need_a_span_that_lasts():
    with pytest.raises(MusicError):
        on_beat.alternate(GRID, 2.0, 2.0)
