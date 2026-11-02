"""Reading a rotation back into a joint's controls, for every order and sign of the canonical axes."""

import itertools
import math
import random

import pytest

from srstudio.limbs.math3d import Quaternion, Vec3
from srstudio.skeleton._rotation import angle_of, compose, decompose, turn

X, Y, Z = Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)
ORDERS = [
    tuple(axis * sign for axis, sign in zip(order, signs, strict=True))
    for order in itertools.permutations((X, Y, Z))
    for signs in itertools.product((1, -1), repeat=3)
]


def same(a: Quaternion, b: Quaternion, tolerance: float = 1e-9) -> bool:
    return angle_of(a.inverse() * b) < tolerance


@pytest.mark.parametrize("axes", ORDERS)
def test_three_axes_rebuild_any_rotation(axes):
    rng = random.Random(11)
    for _ in range(50):
        angles = tuple(rng.uniform(-math.pi, math.pi) for _ in range(3))
        q = compose(axes, angles)
        found, residual = decompose(q, axes, (0.0, 0.0, 0.0))
        assert residual < 1e-9
        assert same(compose(axes, found), q)


@pytest.mark.parametrize("axes", ORDERS)
def test_a_reference_selects_the_branch_it_is_nearest(axes):
    angles = (0.4, 2.3, -0.7)  # a middle angle past a right angle is the far branch of plain Tait-Bryan
    found, residual = decompose(compose(axes, angles), axes, angles)
    assert residual < 1e-9
    assert found == pytest.approx(angles)


@pytest.mark.parametrize("axes", ORDERS)
@pytest.mark.parametrize("middle", [math.pi / 2, -math.pi / 2])
def test_a_gimbal_lock_keeps_the_reference_for_the_last_angle(axes, middle):
    angles = (0.3, middle, -0.5)
    found, residual = decompose(compose(axes, angles), axes, angles)
    assert residual < 1e-7
    assert found[2] == pytest.approx(-0.5, abs=1e-6)
    assert same(compose(axes, found), compose(axes, angles), 1e-7)


def test_two_axes_report_the_turn_they_cannot_hold():
    held, residual = decompose(compose((Z, Y), (0.3, -0.4)), (Z, Y), (0.0, 0.0))
    assert held == pytest.approx((0.3, -0.4)) and residual < 1e-9
    _, residual = decompose(compose((Z, Y, X), (0.3, -0.4, 0.2)), (Z, Y), (0.0, 0.0))
    assert residual == pytest.approx(0.2, abs=1e-6)


def test_one_axis_reads_its_twist_and_reports_the_rest():
    held, residual = decompose(turn(Z * -1, 1.1), (Z * -1,), (0.0,))
    assert held == pytest.approx((1.1,)) and residual < 1e-9
    _, residual = decompose(turn(Z, 0.6) * turn(X, 0.25), (Z,), (0.0,))
    assert residual == pytest.approx(0.25, abs=1e-6)


def test_limits_choose_the_whole_turn_that_lies_inside_them():
    (angle,), _ = decompose(turn(X, -3.0), (X,), (0.0,), [(0.0, 3.5)])
    assert angle == pytest.approx(math.tau - 3.0)
    (angle,), _ = decompose(turn(X, -3.0), (X,), (0.0,), [(0.0, 1.0)])
    assert angle == pytest.approx(-3.0)  # nothing fits, so the nearest is reported and the caller refuses it


def test_turn_of_nothing_is_the_identity():
    assert turn(X, 0.0) == Quaternion()
    assert angle_of(Quaternion()) == 0.0
