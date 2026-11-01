"""A Cutout figure on its marks: cut to a place, or walk there with a bob a stride."""

from __future__ import annotations

import pytest

from srstudio import cutout_walk
from srstudio.cutout_walk import CutoutWalkError, walk
from support.tip_tablet import canvas


def test_a_figure_that_stays_put_takes_no_stride():
    assert cutout_walk.footfalls([(0.0, 300.0), (4.0, 300.0)]) == ()


def test_a_walk_lands_a_foot_every_stride_and_the_last_on_its_mark():
    falls = cutout_walk.footfalls([(1.0, 900.0), (2.0, 500.0)], stride=0.25)
    assert falls == pytest.approx((1.25, 1.5, 1.75, 2.0))


def test_a_walk_that_does_not_divide_takes_the_nearest_stride_that_does():
    falls = cutout_walk.footfalls([(1.0, 900.0), (2.0, 500.0)], stride=0.3)
    assert falls == pytest.approx((1 + 1 / 3, 1 + 2 / 3, 2.0))


def test_a_cut_is_two_rows_at_one_time_and_takes_no_stride():
    assert cutout_walk.footfalls([(0.0, 300.0), (2.0, 300.0), (2.0, 800.0), (3.0, 800.0)]) == ()


def test_the_bob_lifts_between_footfalls_and_lands_on_them():
    rows = [(1.0, 900.0), (2.0, 500.0)]
    bob = dict(cutout_walk.bob(rows, 1000.0, stride=0.5, lift=10.0))
    assert bob[1.0] == bob[1.5] == bob[2.0] == 1000.0
    assert bob[1.25] == bob[1.75] == 990.0


def test_the_bob_never_rises_while_a_figure_stands():
    rows = [(0.0, 900.0), (1.0, 900.0), (2.0, 500.0), (3.0, 500.0)]
    assert {y for t, y in cutout_walk.bob(rows, 1000.0, stride=0.5) if t <= 1.0 or t >= 2.0} == {1000.0}


def test_a_cut_lands_on_its_frame_with_no_slide():
    assert cutout_walk.track([(0.0, 300.0), (2.0, 300.0), (2.0, 800.0)]) == [
        (0.0, 300.0),
        (pytest.approx(2.0 - cutout_walk.CUT), 300.0),
        (2.0, 800.0),
    ]


def test_walk_keys_the_node_and_gives_back_the_footfalls():
    cv = canvas()
    node = cv.group(cv.comp, "figure", x=900, y=1000)
    falls = walk(cv, node, [(1.0, 900.0), (2.0, 500.0)], 1000.0, stride=0.25)
    assert len(falls) == 4
    drawn = cv.scene.to_bytes().decode()
    assert "rotation" in drawn


def test_a_figure_that_only_cuts_does_not_sway():
    cv = canvas()
    node = cv.group(cv.comp, "figure", x=300, y=1000)
    assert walk(cv, node, [(0.0, 300.0), (1.0, 300.0), (1.0, 800.0)], 1000.0) == ()
    assert "rotation" not in cv.scene.to_bytes().decode()


@pytest.mark.parametrize(
    "rows, why",
    [
        ([(1.0, 900.0)], "at least two"),
        ([(2.0, 900.0), (1.0, 500.0)], "backwards"),
        ([(0.0, float("nan")), (1.0, 500.0)], "numbers"),
        ([(-1.0, 900.0), (1.0, 500.0)], "before"),
        ([(0.0, 900.0), (0.1, 100.0)], "too fast"),
    ],
)
def test_a_walk_that_cannot_be_walked_is_refused(rows, why):
    with pytest.raises(CutoutWalkError, match=why):
        cutout_walk.footfalls(rows)


@pytest.mark.parametrize("stride", [0.0, -1.0, float("inf")])
def test_a_stride_takes_a_positive_time(stride):
    with pytest.raises(CutoutWalkError, match="stride"):
        cutout_walk.footfalls([(0.0, 900.0), (1.0, 500.0)], stride=stride)


def test_no_frame_lands_in_the_slide_of_a_cut_near_a_frame():
    """A cut 0.3 ms after a frame: the camera holds until the cut, so that frame must still have the old place."""
    cut = 9.5003
    keys = cutout_walk.track([(0.0, 800.0), (cut, 800.0), (cut, 620.0), (12.0, 620.0)])
    begin, end = [t for t, _ in keys][1:3]
    assert not any(begin <= n / 30 < end for n in range(360))
