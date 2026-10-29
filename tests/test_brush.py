"""The brush: splines, strokes with pressure, outlines and rims, ellipses and the transforms; refused measures."""

import math

import pytest

from srstudio import brush

SQUARE = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]


def test_a_spline_passes_through_its_control_points():
    open_curve = brush.spline([(0, 0), (10, 10), (20, 0)], steps=4)
    assert open_curve[0] == (0, 0) and open_curve[4] == (10, 10) and open_curve[-1] == (20, 0)
    assert len(open_curve) == 9
    closed = brush.spline(SQUARE, closed=True, steps=2)
    assert len(closed) == 8 and closed[0] == (0, 0) and closed[2] == (100, 0) and closed[-1] != closed[0]


def test_a_stroke_is_a_closed_band_of_the_weight_with_round_ends():
    shape = brush.stroke([(0, 50), (100, 50)], 10, brush.EVEN)
    assert (len(shape) - 2) % 6 == 0 and len(shape) > 40
    x0, y0, x1, y1 = brush.bounds(shape)
    assert -6 <= x0 <= -4 and 104 <= x1 <= 106  # the caps add half the weight at each end
    assert 44 <= y0 <= 46.5 and 53.5 <= y1 <= 56  # EVEN breathes a little, never more than a tenth
    tapered = brush.stroke([(0, 50), (100, 50)], 10)
    tx0, ty0, tx1, ty1 = brush.bounds(tapered)
    assert ty1 - ty0 < y1 - y0 and tx0 > x0  # a tapered stroke is thinner at its tips, so its caps are smaller
    assert brush.TAPERED.at(0.5) > brush.TAPERED.at(0.0) > brush.TAPERED.at(1.0)
    assert all(brush.TAPERED.at(s / 20) >= 0.15 for s in range(21))


def test_outline_and_rim_wrap_the_same_points_the_rim_pushed_out_by_the_weight():
    fill = brush.outline(SQUARE)
    ink = brush.rim(SQUARE, 6, brush.Pressure(1, 1, 0, 0, 1))
    fx0, fy0, fx1, fy1 = brush.bounds(fill)
    ix0, iy0, ix1, iy1 = brush.bounds(ink)
    assert -15 <= fx0 <= 0 and -15 <= fy0 <= 0 and 100 <= fx1 <= 115 and 100 <= fy1 <= 115  # a rounded square
    assert ix0 == pytest.approx(fx0 - 6, abs=1.5) and ix1 == pytest.approx(fx1 + 6, abs=1.5)
    assert iy0 == pytest.approx(fy0 - 6, abs=1.5) and iy1 == pytest.approx(fy1 + 6, abs=1.5)
    # the push is outward whichever way the points wind
    other = brush.rim(SQUARE[::-1], 6, brush.Pressure(1, 1, 0, 0, 1))
    assert brush.bounds(other) == pytest.approx(brush.bounds(ink), abs=1e-6)


def test_ellipse_shift_rotate_flip_and_bounds():
    e = brush.ellipse(50, 40, 20, 10)
    assert len(e) == 26 and brush.bounds(e) == (30, 30, 70, 50)
    assert brush.bounds(brush.shift(e, 5, -5)) == (35, 25, 75, 45)
    turned = brush.ellipse(50, 40, 20, 10, tilt=90)
    assert brush.bounds(turned) == pytest.approx((40, 20, 60, 60), abs=0.01)
    assert brush.bounds(brush.rotate(e, 50, 40, 90)) == pytest.approx((40, 20, 60, 60), abs=0.01)
    # a clockwise turn (y down) moves a point above the pivot to the right
    up = brush.rotate((0.0, -10.0), 0, 0, 90)
    assert up == pytest.approx((10, 0), abs=0.01)
    assert brush.bounds(brush.flip(e, 0)) == (-70, 30, -30, 50)


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda: brush.stroke([(0, 0)], 5), "at least 2 points"),
        (lambda: brush.stroke([(0, 0), (1, 1)], 0), "weight must be a positive"),
        (lambda: brush.stroke([(0, 0), (1, math.nan)], 5), "not a finite point"),
        (lambda: brush.stroke([(0, 0), (0, 0)], 5), "all in one place"),
        (lambda: brush.outline([(0, 0), (1, 1)]), "at least 3 points"),
        (lambda: brush.rim([(0, 0), (1, 1)], 5), "at least 3 points"),
        (lambda: brush.rim(SQUARE, -1), "weight must be a positive"),
        (lambda: brush.ellipse(0, 0, 0, 5), "rx must be a positive"),
        (lambda: brush.ellipse(0, 0, 5, math.inf), "ry must be a positive"),
        (lambda: brush.spline([(0, 0, 0), (1, 1)]), "not a finite point"),
    ],
)
def test_bad_measures_are_refused(call, match):
    with pytest.raises(brush.BrushError, match=match):
        call()
