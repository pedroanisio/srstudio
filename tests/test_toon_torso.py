"""The Toon torso (ADR 0049): one smooth neck-shoulder-flank contour built from a few numbers under any head, and an
arm drawn inside it, tapering into the body like the traced cat's instead of a lobe stacked on the shoulder."""

import math

import pytest

from srstudio import brush, toon_cast, toon_torso
from srstudio.toon import ToonDataError
from srstudio.toon_torso import Torso
from support.toon_contour import bends, inside, points, sharpest, sides

HEAD = (  # a plain round head from the left neck join over the crown to the right one, meeting the neck heading down
    (104.0, 690.0), (98.0, 660.0), (94.0, 620.0), (100.0, 580.0), (122.0, 548.0), (152.0, 530.0), (185.0, 524.0),
    (218.0, 530.0), (248.0, 548.0), (270.0, 580.0), (276.0, 620.0), (272.0, 660.0), (266.0, 690.0),
)  # fmt: skip
BUILDS = {  # (shoulder, slope, flank): sloping out wide, rounded, and almost upright
    "sloping": (120.0, 50.0, 126.0),
    "rounded": (110.0, 55.0, 116.0),
    "upright": (96.0, 65.0, 102.0),
}
GENTLE = 10.0  # the sharpest a shoulder may bulge, in degrees per 8 px: a radius of about 46 px
NECK = 13.5  # the sharpest a neck may curve in, in degrees per 8 px: a radius of about 34 px, never a notch
DESK = [toon_cast.SHOULDERS[0], (82.0, 760.0), (124.0, 792.0)]  # the shared left desk arm, shoulder to wrist
PAW = (132.0, 794.0)


def torso(build: str = "rounded", **kw) -> Torso:
    shoulder, slope, flank = BUILDS[build]
    fields = dict(head=HEAD, shoulder=shoulder, slope=slope, flank=flank, arm=28.0)
    return Torso(**(fields | kw))


# -- the contour -------------------------------------------------------------------------------------------------------
def test_the_head_is_kept_and_the_torso_closes_along_the_base():
    t = torso()
    contour = t.contour
    start = contour.index(HEAD[0])
    assert contour[start : start + len(HEAD)] == HEAD
    assert max(y for _, y in contour) <= t.base + 2.0
    bottom = [p for p in contour if p[1] >= t.base]
    assert min(x for x, _ in bottom) == pytest.approx(t.centre - t.flank, abs=0.01)
    assert max(x for x, _ in bottom) == pytest.approx(t.centre + t.flank, abs=0.01)
    assert len(contour) >= len(HEAD) + 12  # dense enough for the brush to follow
    assert t.contour == torso().contour  # the same every build


@pytest.mark.parametrize("build", BUILDS)
def test_each_side_runs_down_from_the_neck_to_the_base_as_one_gentle_curve(build):
    t = torso(build)
    shape = brush.outline(t.contour, steps=3)
    top = max(HEAD[0][1], HEAD[-1][1])
    runs = sides(shape, top, t.base - 15.0)
    for side, run in runs.items():
        assert len(run) > 10, side
        ys = [y for _, y in run]
        assert all(b > a for a, b in zip(ys, ys[1:], strict=False)), f"{build} {side}: the side turns back up"
    out, inward = sharpest(shape, top, t.base - 15.0)
    assert out <= GENTLE and inward <= NECK, (build, out, inward)
    for run in bends(shape, top, t.base - 15.0).values():  # in at the neck, out over the shoulder: one change
        signs = [b > 0 for b in run if abs(b) > 1.0]
        assert sum(1 for a, b in zip(signs, signs[1:], strict=False) if a != b) <= 1, build


@pytest.mark.parametrize("build", BUILDS)
def test_the_shoulders_sit_where_the_numbers_put_them(build):
    t = torso(build)
    for side, (sx, sy) in zip((-1, 1), t.shoulders, strict=True):
        assert min(math.dist((sx, sy), p) for p in t.contour) < 5.0  # on the outline
        assert sy > HEAD[0][1] and t.shoulder - 45.0 < side * (sx - t.centre) <= t.shoulder + 0.5
        below = [side * (x - t.centre) for x, y in t.contour if sy <= y <= t.base and side * (x - t.centre) > 0]
        assert max(below) >= min(t.shoulder, t.flank) - 0.5  # out to the shoulder, then on to the flank


def test_a_shoulder_too_low_to_fit_above_the_base_is_refused():
    with pytest.raises(ToonDataError, match="shoulders reach"):
        torso("rounded", shoulder=150.0)  # far out on a steep slope


def test_the_edge_is_the_contour_s_outer_x_at_a_height():
    t = torso()
    for side, (sx, sy) in zip((-1, 1), t.shoulders, strict=True):
        assert abs(t.edge(sy, side) - sx) < 1.0
        assert t.edge(t.base, side) == pytest.approx(t.centre + side * t.flank, abs=0.5)
    with pytest.raises(ToonDataError):
        t.edge(HEAD[0][1] - 40.0, -1)  # above the neck the edge is the head's
    with pytest.raises(ToonDataError):
        t.edge(700.0, 0)


@pytest.mark.parametrize(
    "fields",
    [
        dict(head=HEAD[:2]),
        dict(head=((float("nan"), 690.0), *HEAD[1:])),
        dict(shoulder=0.0),
        dict(slope=-5.0),
        dict(slope=90.0),
        dict(flank=-1.0),
        dict(arm=0.0),
        dict(arm=float("inf")),
        dict(base=700.0),  # above the shoulders
        dict(centre=float("nan")),
    ],
)
def test_a_torso_refuses_bad_numbers(fields):
    with pytest.raises(ToonDataError):
        torso(**fields)


def test_the_torso_is_calmer_than_the_head_under_a_hand_s_drift():
    t = torso()
    weights = t.weights(0.2)
    assert len(weights) == len(t.contour)
    start = t.contour.index(HEAD[0])
    assert weights[start : start + len(HEAD)] == (1.0,) * len(HEAD)
    assert set(weights[:start] + weights[start + len(HEAD) :]) == {0.2}
    with pytest.raises(ToonDataError):
        t.weights(1.5)
    calm = brush.wobble(t.contour, 2.0, steps=1, seed=3, weights=weights)
    moved = [math.dist(a, b) for a, b in zip(calm, t.contour, strict=True)]
    assert max(moved[:start]) <= 0.2 * 2.0 + 0.01
    assert max(moved[start : start + len(HEAD)]) > 0.2 * 2.0 + 0.2


# -- the arm -----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("build", BUILDS)
@pytest.mark.parametrize(
    "reach",
    [
        [(308.0, 712.0), (352.0, 742.0), (398.0, 762.0)],  # over to a keyboard
        [(308.0, 712.0), (352.0, 742.0), (398.0, 771.0)],  # the same arm on the other typing frame
        [(308.0, 712.0), (330.0, 750.0), (360.0, 788.0)],  # out over the desk's edge
        [(62.0, 712.0), (18.0, 742.0), (-28.0, 762.0)],  # the same, mirrored
    ],
)
def test_an_arm_reaching_out_past_its_flank_leaves_the_body_without_doubling_back(build, reach):
    t = torso(build)
    drawn = t.arm_path(reach)
    side = 1 if reach[0][0] > 185.0 else -1
    line = brush.spline(drawn, False, 8)
    assert all(side * (b[0] - a[0]) > 0 for a, b in zip(line, line[1:], strict=False))  # no hook at the top
    assert drawn[-1] == reach[-1]
    assert side * (t.edge(drawn[0][1], side) - drawn[0][0]) > 0  # it still starts inside the outline


@pytest.mark.parametrize("build", BUILDS)
def test_an_arm_starts_inside_the_body_below_the_shoulder_and_ends_where_asked(build):
    t = torso(build)
    for side, path in ((-1, DESK), (1, [(2 * 185.0 - x, y) for x, y in DESK])):
        drawn = t.arm_path(path)
        (sx, sy) = t.shoulders[0 if side < 0 else 1]
        x0, y0 = drawn[0]
        assert y0 > sy  # under the shoulder line, never on it
        assert side * (t.edge(y0, side) - x0) >= t.arm * 0.5 - 0.01  # well inside the outline
        assert drawn[-1] == path[-1] and len(drawn) == len(path)
    with pytest.raises(ToonDataError):
        t.arm_path([DESK[0]])


def test_an_elbow_outside_the_body_is_pulled_in_and_the_rest_is_left_to_reach():
    t = torso("sloping")
    path = [toon_cast.SHOULDERS[1], (352.0, 760.0), (262.0, 792.0)]  # an elbow out past the flank, the paw back in
    drawn = t.arm_path(path)
    assert t.edge(drawn[1][1], 1) - drawn[1][0] >= t.arm * 0.5 and drawn[1][1] >= 760.0
    assert drawn[-1] == (262.0, 792.0)


@pytest.mark.parametrize("build", BUILDS)
def test_an_arm_s_layers_stay_inside_the_body_above_the_shoulder_line(build):
    t = torso(build)
    body = brush.outline(t.contour, steps=3)
    level = max(y for _, y in t.shoulders)
    layers, at, way = t.limb(DESK, PAW, "#888888", "#444444")
    assert [c for _, c in layers] == ["ink", "#888888", "#444444"]
    assert at == PAW  # a paw low on the desk stays where the pose puts it
    for shape, _ in layers:
        for x, y in points(shape):
            assert inside(body, x, y) or y > level, (build, x, y)
    drawn = t.arm_path(DESK)
    dx, dy = PAW[0] - drawn[-2][0], PAW[1] - drawn[-2][1]
    assert way == pytest.approx((dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)))


@pytest.mark.parametrize("build", BUILDS)
def test_a_paw_raised_to_the_face_crosses_the_neck_between_the_shoulders(build):
    t = torso(build)
    path = [toon_cast.SHOULDERS[1], (294.0, 700.0), (233.0, 664.0)]
    layers, at, _ = t.limb(path, (215.0, 652.0), "#888888", "#444444")
    assert at == (215.0, 652.0)  # on the face, where the pose puts it
    (lx, _), (rx, _) = t.shoulders
    level = max(y for _, y in t.shoulders)
    assert all(y > level or lx < x < rx for shape, _ in layers for x, y in points(shape))
    drawn = t.arm_path(path)
    assert side_clear(t, drawn)


def side_clear(t: Torso, drawn) -> bool:
    x, y = drawn[1]
    return t.edge(y, 1) - x >= t.arm * 0.5 - 0.01  # the elbow stays inside


def test_a_paw_beside_the_shoulders_is_kept_inside_and_a_point_elsewhere_is_left_alone():
    t = torso()
    (_, sy), _ = t.shoulders
    y = sy - 4.0
    x = t.edge(y, 1) + 12.0
    kept = t.keep((x, y), 10.0)
    assert kept[0] < t.edge(kept[1], 1)
    assert 10.0 <= min(math.dist(kept, p) for p in t.contour) < 26.0  # just inside, not across the chest
    assert t.keep((300.0, 600.0), 10.0) == (300.0, 600.0)  # up on the head
    assert t.keep((404.0, 790.0), 10.0) == (404.0, 790.0)  # below the shoulders, reaching out
    assert t.keep((t.centre, y), 10.0) == (t.centre, y)  # already well inside


def test_an_arm_that_cannot_clear_the_outline_is_refused():
    t = torso("upright")
    with pytest.raises(ToonDataError, match="cannot stay inside"):
        t.arm_path([toon_cast.SHOULDERS[1], (290.0, 760.0), (330.0, 640.0), (420.0, 700.0)])


def test_an_arm_tapers_into_the_body_and_is_widest_toward_the_paw():
    t = torso()
    layers, _, _ = t.limb(DESK, PAW, "#888888", "#444444")
    coat = points(layers[1][0])
    drawn = t.arm_path(DESK)

    def across(at, toward):  # the coat's width through ``at``, square to the way toward ``toward``
        ux, uy = toward[0] - at[0], toward[1] - at[1]
        length = math.hypot(ux, uy)
        ux, uy = ux / length, uy / length
        slab = [(x - at[0]) * -uy + (y - at[1]) * ux for x, y in coat if abs((x - at[0]) * ux + (y - at[1]) * uy) < 2.5]
        return max(slab) - min(slab)

    line = brush.spline(drawn, False, 8)
    assert across(line[0], line[3]) < t.arm * 0.45  # a thin start, like a crease into the body
    assert across(line[-1], line[-4]) > t.arm * 0.9  # a full forearm at the wrist


@pytest.mark.parametrize("build", BUILDS)
def test_arm_lines_ink_an_arm_over_the_body_and_never_along_the_flank(build):
    t = torso(build)
    inks = toon_torso.arm_lines(t.arm_path(DESK), t.arm, t.contour, toon_torso.TAPER, 2.0)
    assert inks  # the edge across the chest is a line
    assert len(inks) < 4  # lifted, not a closed outline
    assert not any(0 < toon_torso.depth_in(t.contour, p)[0] < 4.0 for shape in inks for p in points(shape)[::4])


def test_depth_in_is_how_far_inside_and_the_way_of_the_nearest_edge():
    square = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))
    depth, way = toon_torso.depth_in(square, (30.0, 50.0))
    assert (depth, way) == (pytest.approx(30.0), pytest.approx((0.0, -1.0)))
    assert toon_torso.depth_in(square, (-20.0, 50.0))[0] == pytest.approx(-20.0)


def test_arm_lines_leave_out_an_edge_running_just_inside_the_body():
    tall = ((0.0, 0.0), (100.0, 0.0), (100.0, 300.0), (0.0, 300.0))
    along = [(20.0, 20.0), (20.0, 150.0), (20.0, 280.0)]  # inside the left edge, its left edge merged with the body
    lines = toon_torso.arm_lines(along, 30.0, tall, brush.Pressure(1.0, 1.0, 0.0, 0.0, 1.0), 2.0)
    assert len(lines) == 1
    assert all(p[0] > 20.0 for p in points(lines[0]))


def test_an_arm_merged_with_the_body_on_both_sides_has_no_line():
    narrow = ((0.0, 0.0), (20.0, 0.0), (20.0, 300.0), (0.0, 300.0))
    even = brush.Pressure(1.0, 1.0, 0.0, 0.0, 1.0)
    assert toon_torso.arm_lines([(10.0, 20.0), (10.0, 150.0), (10.0, 280.0)], 16.0, narrow, even, 2.0) == []


def test_the_module_is_reachable_from_the_package():
    assert toon_torso.Torso is Torso
