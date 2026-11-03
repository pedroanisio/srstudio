"""A jog fitted to any figure's drawn legs bobs by the amount asked, never by the reference's foreshortening."""

from __future__ import annotations

import math

import pytest

from srstudio import jog_fit
from srstudio.errors import SrstudioError
from srstudio.jog_fit import JogFitError, fit_jog
from srstudio.stick import RigPose
from srstudio.stick_door import JOG


def ref(far_leg: float, near_leg: float, *, torso: float = 333.0, neck: float = 107.0) -> RigPose:
    """A standing figure whose far and near legs are drawn ``far_leg`` and ``near_leg`` long, thigh and shin half each,
    as a dance pose foreshortens one leg against the other."""
    hip = (540.0, 1000.0)
    knees = ((540.0, hip[1] + far_leg / 2), (540.0, hip[1] + near_leg / 2))
    feet = ((540.0, hip[1] + far_leg), (540.0, hip[1] + near_leg))
    neck_at = (540.0, hip[1] - torso)
    return RigPose(
        head=(540.0, neck_at[1] - neck),
        neck=neck_at,
        hip=hip,
        knees=knees,
        feet=feet,
        elbows=((480.0, neck_at[1] + 120), (600.0, neck_at[1] + 120)),
        hands=((470.0, neck_at[1] + 230), (610.0, neck_at[1] + 230)),
        toes=None,
    )


LEGS = [(400.0, 400.0), (394.0, 348.0), (403.0, 420.0), (420.0, 403.0), (500.0, 300.0), (300.0, 500.0)]


def crown_change(fit: dict[str, RigPose]) -> float:
    return fit["jog-a"].head[1] - fit["jog-b"].head[1]


def leg(pose: RigPose, side: int) -> float:
    return math.dist(pose.hip, pose.knees[side]) + math.dist(pose.knees[side], pose.feet[side])


def support(pose: RigPose) -> int:
    return 0 if pose.feet[0][1] >= pose.feet[1][1] else 1


@pytest.mark.parametrize(("far", "near"), LEGS)
def test_the_crown_change_between_the_drawings_is_the_bob_asked_whatever_the_reference_legs(
    far: float, near: float
) -> None:
    fit = fit_jog(ref(far, near), bob=6.8)
    assert crown_change(fit) == pytest.approx(6.8, abs=1e-6)


def test_an_uneven_foreshortened_pair_cannot_double_the_bob() -> None:
    even, uneven = fit_jog(ref(411.5, 411.5), bob=6.8), fit_jog(ref(403.0, 420.0), bob=6.8)
    assert crown_change(uneven) == pytest.approx(crown_change(even), abs=1e-6)


@pytest.mark.parametrize(("far", "near"), LEGS)
def test_both_drawings_stand_on_legs_of_one_length(far: float, near: float) -> None:
    fit = fit_jog(ref(far, near), bob=6.8)
    a, b = fit["jog-a"], fit["jog-b"]
    assert leg(a, support(a)) == pytest.approx(leg(b, support(b)), rel=1e-6)


def test_the_support_leg_is_the_reference_s_least_foreshortened_bones() -> None:
    fit = fit_jog(ref(403.0, 420.0), bob=6.8)
    a = fit["jog-a"]
    assert leg(a, support(a)) == pytest.approx(420.0, rel=1e-6)


def test_the_raised_leg_keeps_the_drawing_s_own_foreshortening() -> None:
    fit = fit_jog(ref(400.0, 400.0), bob=6.8)
    for name in ("jog-a", "jog-b"):
        t, f = JOG[name], fit[name]
        s = support(t)
        assert leg(f, 1 - s) / leg(f, s) == pytest.approx(leg(t, 1 - s) / leg(t, s), rel=1e-6)


def test_jog_a_keeps_the_template_s_planted_foot_and_hip_x() -> None:
    fit = fit_jog(ref(394.0, 348.0), bob=6.8)
    a, t = fit["jog-a"], JOG["jog-a"]
    assert max(f[1] for f in a.feet) == pytest.approx(max(f[1] for f in t.feet))
    assert fit["jog-a"].hip[0] == pytest.approx(t.hip[0]) and fit["jog-b"].hip[0] == pytest.approx(JOG["jog-b"].hip[0])


def test_the_upper_body_takes_the_reference_s_lengths() -> None:
    fit = fit_jog(ref(400.0, 400.0, torso=300.0, neck=90.0), bob=6.8)
    for p in fit.values():
        assert math.dist(p.hip, p.neck) == pytest.approx(300.0)
        assert math.dist(p.neck, p.head) == pytest.approx(90.0)


def test_a_zero_bob_holds_the_crown_still() -> None:
    assert crown_change(fit_jog(ref(403.0, 420.0), bob=0.0)) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("bob", [-1.0, math.nan, math.inf, True, "6.8"])
def test_a_bob_that_is_not_a_height_raises(bob: object) -> None:
    with pytest.raises(JogFitError):
        fit_jog(ref(400.0, 400.0), bob=bob)  # type: ignore[arg-type]


def test_a_bob_as_long_as_the_leg_raises() -> None:
    with pytest.raises(JogFitError):
        fit_jog(ref(400.0, 400.0), bob=400.0)


def test_a_reference_with_a_zero_length_bone_raises() -> None:
    bad = ref(400.0, 400.0)
    flat = RigPose(bad.head, bad.neck, bad.hip, (bad.hip, bad.knees[1]), bad.feet, bad.elbows, bad.hands, None)
    with pytest.raises(JogFitError):
        fit_jog(flat, bob=6.8)


def test_the_error_is_a_library_error() -> None:
    assert issubclass(JogFitError, SrstudioError) and issubclass(JogFitError, ValueError)


def test_the_template_is_the_door_jog() -> None:
    assert jog_fit.TEMPLATE is JOG
