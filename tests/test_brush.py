"""The brush: splines, strokes with pressure, outlines and rims, inked rims and hand-wobbled contours, ellipses and
the transforms; refused measures."""

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


def circle(r: float = 50.0, n: int = 24) -> list[tuple[float, float]]:
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def test_a_hand_presses_heavier_where_the_outline_turns_from_the_light_and_lighter_at_sharp_tips():
    hand = brush.HAND
    down, up = (0.0, 1.0), (0.0, -1.0)  # the default weight falls down and to the back
    for k in range(11):
        s = k / 10
        assert hand.at(down, 0.0, s) > 2 * hand.at(up, 0.0, s)
        assert hand.at(down, math.pi / 2, s) < 0.6 * hand.at(down, 0.0, s)  # a convex tip thins the line
        assert hand.at(down, -math.pi / 2, s) == pytest.approx(hand.at(down, 0.0, s))  # a hollow does not
        assert hand.at(up, math.pi, s) > 0  # never nothing
    grain = {round(hand.at(down, 0.0, k / 40), 4) for k in range(41)}
    assert len(grain) > 20  # the pressure is uneven along the way


def test_an_inked_rim_is_heavy_at_the_bottom_thin_at_the_top_and_its_points_wind_either_way():
    fill = brush.outline(circle())
    ink = brush.inked(circle(), 10.0)
    fx0, fy0, fx1, fy1 = brush.bounds(fill)
    ix0, iy0, ix1, iy1 = brush.bounds(ink)
    assert (len(ink) - 2) % 6 == 0
    assert iy1 - fy1 > 2 * (fy0 - iy0) > 0  # under the circle the band is more than twice as wide as over it
    # pushed outward whichever way the points wind (the grain runs the other way round, so not to the pixel)
    assert brush.bounds(brush.inked(circle()[::-1], 10.0)) == pytest.approx((ix0, iy0, ix1, iy1), abs=2.0)
    light = brush.Hand(toward=(0.0, -1.0))  # the weight can fall any way: here on the top
    lx0, ly0, lx1, ly1 = brush.bounds(brush.inked(circle(), 10.0, light))
    assert fy0 - ly0 > 2 * (ly1 - fy1)


def test_a_wobbled_contour_is_dense_uneven_and_the_same_every_time():
    smooth = brush.spline(circle(), closed=True, steps=4)
    hand = brush.wobble(circle(), 3.0, steps=4)
    assert len(hand) == len(smooth) == 96
    gaps = [math.dist(a, b) for a, b in zip(hand, smooth, strict=True)]
    assert max(gaps) <= 3.0 + 1e-6 and max(gaps) > 1.5 and len({round(g, 2) for g in gaps}) > 40
    assert brush.wobble(circle(), 3.0, steps=4) == hand  # no randomness: a build draws the same line
    assert brush.wobble(circle(), 3.0, steps=4, seed=1) != hand
    assert all(math.dist(p, q) < 1e-9 for p, q in zip(brush.wobble(circle(), 0.0, steps=4), smooth, strict=True))
    line = brush.wobble([(0.0, 0.0), (100.0, 0.0)], 2.0, closed=False, steps=10)
    assert line[0] == pytest.approx((0.0, 0.0), abs=2.0) and len(line) == 11  # an open line keeps its ends


def sampled(shape: brush.Shape, k: int = 6) -> list[tuple[float, float]]:
    """The shape's outline as a polygon: each cubic sampled ``k`` times."""
    out, (x0, y0) = [], (shape[0], shape[1])
    for i in range(2, len(shape), 6):
        c1x, c1y, c2x, c2y, x, y = shape[i : i + 6]
        for j in range(1, k + 1):
            t, u = j / k, 1 - j / k
            out.append(
                (
                    u**3 * x0 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t**3 * x,
                    u**3 * y0 + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t**3 * y,
                )
            )
        x0, y0 = x, y
    return out


def inside(poly: list[tuple[float, float]], x: float, y: float) -> bool:
    hit = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit


def test_a_ragged_hand_breaks_the_band_s_edge_at_a_fine_scale():
    calm, ragged = brush.Hand(), brush.Hand(ragged=0.25)
    assert all(calm.at((0.0, 1.0), 0.0, k / 50) == brush.HAND.at((0.0, 1.0), 0.0, k / 50) for k in range(51))

    def turns(hand: brush.Hand) -> int:  # how often the width changes direction along the way
        w = [hand.at((0.0, 1.0), 0.0, k / 400) for k in range(401)]
        d = [b - a for a, b in zip(w, w[1:], strict=False)]
        return sum((a > 0) != (b > 0) for a, b in zip(d, d[1:], strict=False))

    assert turns(ragged) > 4 * turns(calm)


def test_a_broken_band_lifts_the_brush_in_as_many_places_as_asked():
    even = brush.Hand(light=1.0, heavy=1.0, tips=0.0, grain=0.0)
    pieces = brush.broken(circle(), 6.0, even, breaks=4, seed=3)
    assert len(pieces) == 4 and all((len(s) - 2) % 6 == 0 for s in pieces)
    polys = [sampled(s) for s in pieces]
    covered = []
    for k in range(360):
        a = 2 * math.pi * k / 360
        x, y = 53.0 * math.cos(a), 53.0 * math.sin(a)  # halfway across the band
        covered.append(any(inside(p, x, y) for p in polys))
    assert 0.7 < sum(covered) / 360 < 0.97  # mostly inked, with gaps
    assert sum(a and not b for a, b in zip(covered, covered[1:] + covered[:1], strict=True)) == 4  # four gaps
    assert brush.broken(circle(), 6.0, even, breaks=4, seed=3) == pieces  # seeded: the same every build
    assert brush.broken(circle(), 6.0, even, breaks=4, seed=4) != pieces
    assert len(brush.broken(circle(), 6.0, breaks=3)) == 3


def test_a_lump_is_an_uneven_one_off_blob_round_its_centre():
    a = brush.lump(10.0, 20.0, 8.0, 6.0, 0.15, seed=1)
    assert a == brush.lump(10.0, 20.0, 8.0, 6.0, 0.15, seed=1) != brush.lump(10.0, 20.0, 8.0, 6.0, 0.15, seed=2)
    assert len(a) != len(brush.ellipse(10.0, 20.0, 8.0, 6.0))  # not the four arcs of a perfect ellipse
    x0, y0, x1, y1 = brush.bounds(a)
    assert 10.0 - 8.0 * 1.25 < x0 < 10.0 - 8.0 * 0.75 and 10.0 + 8.0 * 0.75 < x1 < 10.0 + 8.0 * 1.25
    assert 20.0 - 6.0 * 1.25 < y0 < 20.0 - 6.0 * 0.75 and 20.0 + 6.0 * 0.75 < y1 < 20.0 + 6.0 * 1.25
    assert brush.bounds(brush.lump(0.0, 0.0, 8.0, 6.0, 0.15, seed=1, tilt=90.0))[3] > 6.0 * 1.1  # turned


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
        (lambda: brush.inked([(0, 0), (1, 1)], 5), "at least 3 points"),
        (lambda: brush.inked(SQUARE, 0), "weight must be a positive"),
        (lambda: brush.inked(SQUARE, 5, brush.Hand(light=-1.0)), "light must be a positive"),
        (lambda: brush.inked(SQUARE, 5, brush.Hand(toward=(0.0, 0.0))), "toward must be a direction"),
        (lambda: brush.wobble(SQUARE, -1.0), "amount must be a non-negative"),
        (lambda: brush.wobble(SQUARE, math.nan), "amount must be a non-negative"),
        (lambda: brush.wobble([(0, 0)], 1.0), "at least 2 points"),
        (lambda: brush.broken(SQUARE, 5, breaks=0), "breaks must be a whole number of at least 1"),
        (lambda: brush.broken(SQUARE, 5, gap=0.0), "gap must be a positive"),
        (lambda: brush.broken(SQUARE, 5, breaks=5, gap=90.0), "the gaps would take half the contour"),
        (lambda: brush.broken(SQUARE, 5, steps=1, breaks=3), "piece 1 of 3 is too short to draw"),
        (lambda: brush.lump(0, 0, 0, 5, 0.1), "rx must be a positive"),
        (lambda: brush.lump(0, 0, 5, 5, 0.6), "amount must be a number from 0 to 0.5"),
        (lambda: brush.lump(0, 0, 5, 5, 0.1, points=3), "points must be a whole number of at least 5"),
    ],
)
def test_bad_measures_are_refused(call, match):
    with pytest.raises(brush.BrushError, match=match):
        call()
