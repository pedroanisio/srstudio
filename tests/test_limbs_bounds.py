"""Extreme authoring input must fail through typed validation before scene mutation."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, LimbError
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.interaction import Participant, bake_interaction
from srstudio.limbs.math3d import number
from srstudio.limbs.motion import Action, Motion


def test_huge_integer_is_a_typed_validation_error():
    with pytest.raises(LimbError, match="finite"):
        number(10**1000, "oversized")


def test_action_rejects_overflow_of_its_end_time():
    with pytest.raises(LimbError, match="end"):
        Action("point", start=1e308, duration=1e308)


@pytest.mark.parametrize("backend", ["auto", "native", "baked", "interaction"])
def test_resolved_huge_duration_fails_budget_before_multiplication_overflow_or_mutation(backend):
    cv = Canvas(Scene())
    m = Motion(ArmProfile(), HUMAN, (Action("point", duration=1e308),))
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError) as error:
        if backend == "interaction":
            bake_interaction(cv, cv.comp, (Participant("right", m),), (), id="huge")
        else:
            compile_motion(cv, cv.comp, m, id="huge", backend=backend)
    assert error.value.code == "budget"
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize("duration", [1e-9, 1.00000001])
def test_unrepresentable_frame_intervals_fail_before_drawing(duration):
    cv = Canvas(Scene())
    m = Motion(ArmProfile(), HUMAN)
    before = cv.scene.to_bytes()
    with pytest.raises(LimbError, match="resolution|interval"):
        compile_motion(cv, cv.comp, m, id="tiny", backend="baked", options=BakeOptions(fps=24, duration=duration))
    assert cv.scene.to_bytes() == before


def test_offset_must_preserve_a_frame_interval_in_float_arithmetic():
    with pytest.raises(LimbError, match="offset"):
        BakeOptions(offset=1e308)


def test_large_finite_rotations_and_directions_normalize_without_overflow():
    import math

    from srstudio.limbs import Quaternion, Vec3

    unit = Vec3(1.5e308, 1.5e308, 1.5e308).unit()
    assert unit.length == pytest.approx(1)
    assert unit.x == pytest.approx(1 / math.sqrt(3))
    q = Quaternion(1e308, 1e308, 1e308, 1e308)
    assert (q.w, q.x, q.y, q.z) == pytest.approx((0.5, 0.5, 0.5, 0.5))
    assert q.rotate(Vec3(1, 0, 0)).length == pytest.approx(1)


def test_rotation_basis_rejects_shear_scale_and_reflection():
    from srstudio.limbs import Quaternion, Vec3

    for axes in (
        (Vec3(), Vec3(0, 1, 0), Vec3(0, 0, 1)),
        (Vec3(1, 0, 0), Vec3(1, 1, 0), Vec3(0, 0, 1)),
        (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, -1)),
    ):
        with pytest.raises(LimbError, match="basis"):
            Quaternion.axes(*axes)


def test_large_but_incrementable_offset_still_requires_microsecond_clock_resolution():
    with pytest.raises(LimbError, match="offset"):
        BakeOptions(offset=2**46, fps=120)


def test_derived_anatomical_lengths_must_remain_finite():
    from srstudio.limbs import Vec3
    from srstudio.limbs.model import DigitProfile

    with pytest.raises(LimbError, match="length"):
        ArmProfile(upper=1e308, forearm=1e308)
    with pytest.raises(LimbError, match="length"):
        DigitProfile("unbounded", Vec3(), (1e308, 1e308))


def test_mixed_type_object_keys_are_typed_schema_errors():
    from srstudio.limbs.serialization import motion_dict, parse_motion

    for where in ("document", "motion"):
        data = motion_dict(Motion(ArmProfile(), HUMAN))
        node = data if where == "document" else data["motion"]
        node[3] = "invalid"
        node["unexpected"] = "invalid"
        with pytest.raises(LimbError, match="unknown|field"):
            parse_motion(data)


def test_identifier_sizes_are_bounded_before_per_frame_names_can_amplify_input():
    from dataclasses import replace

    from srstudio.limbs import Frame, Vec3
    from srstudio.limbs.model import DigitProfile
    from srstudio.limbs.motion import Attachment, Contact, TransformTrack, WordRef

    constructors = (
        lambda: DigitProfile("x" * 129, Vec3(), (1,)),
        lambda: replace(HUMAN, name="x" * 129),
        lambda: Contact("x" * 129, 0, 1, TransformTrack.constant(Frame())),
        lambda: Attachment("x" * 129, 0, 1, Frame()),
        lambda: WordRef("x" * 129, 0),
        lambda: WordRef("take", 10**1000),
    )
    for construct in constructors:
        with pytest.raises(LimbError):
            construct()


def test_camera_rejects_projection_overflow_and_underflow_at_its_output_boundary():
    from srstudio.limbs import Camera, Vec3

    with pytest.raises(LimbError, match="projected|projection"):
        Camera(scale=1e308).project(Vec3(10, 0, 0))
    with pytest.raises(LimbError, match="projected|projection"):
        Camera(projection="perspective", focal=1e-308).project(Vec3(0, 0, -1e308))
