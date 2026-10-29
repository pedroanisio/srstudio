"""A folded finger must have a solid, simple outline instead of a self-crossing ribbon."""

import math

import pytest

from srstudio.limbs import HUMAN, ArmProfile, Camera, HandControl
from srstudio.limbs.geometry import project_pose
from srstudio.limbs.motion import Action, Motion


def crossing(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return cross(a, b, c) * cross(a, b, d) < -1e-8 and cross(c, d, a) * cross(c, d, b) < -1e-8


@pytest.mark.parametrize("curl", [0.4, 0.65, 0.85, 1])
@pytest.mark.parametrize("twist", [0, math.pi / 2, math.pi])
def test_projected_curled_digits_have_no_crossing_outline_edges(curl, twist):
    m = Motion(ArmProfile(), HUMAN, (Action("grasp", duration=2, control=HandControl(curl=curl, forearm_twist=twist)),))
    pose = project_pose(m.sample(1), Camera(projection="perspective", distance=4, focal=4), width=m.arm.width)
    for part in pose.parts:
        if not part.name.startswith("digit:"):
            continue
        polygon = part.polygon
        edges = list(zip(polygon, (*polygon[1:], polygon[0]), strict=True))
        assert not any(
            crossing(*a, *b)
            for i, a in enumerate(edges)
            for j, b in enumerate(edges)
            if j > i + 1 and not (i == 0 and j == len(edges) - 1)
        ), (curl, twist, part.name)


def test_looping_digit_preserves_a_real_hole_and_styles_emit_even_odd_fill():
    from sr_core.scene import Scene

    from srstudio import Canvas
    from srstudio.limbs.adapters import Appearance, adapter_for
    from srstudio.limbs.geometry import Part, ProjectedPose, path, tube

    line = ((0, 0), (0, 30), (30, 30), (30, 0), (0, 0))
    contour = tube(line, (4, 4, 4, 4, 4))
    assert len(contour.holes) == 1
    assert path(contour.exterior, contour.holes).count("M") == 2
    part = Part("digit:index", contour.exterior, line, 0, 4, "skin", holes=contour.holes)
    pose = ProjectedPose((part,), (0, 0), (0, 0), (0, 0), (), "palm", 0)
    cv = Canvas(Scene())
    adapter_for("toon").draw(cv, cv.comp, pose, Appearance(detail=0), id="loop")
    assert any(n.attributes().get("fillRule") == "evenodd" for n in cv.scene.iter())


def test_end_on_digit_has_a_finite_round_contour_and_fixed_sampling_bounds():
    from srstudio.limbs import LimbError
    from srstudio.limbs.geometry import tube

    contour = tube(((1, 2), (1, 2), (1, 2)), (4, 4, 4))
    assert len(contour.exterior) == 32 and not contour.holes
    assert min(p[0] for p in contour.exterior) == pytest.approx(-1)
    for points, widths in (
        ((), ()),
        (((0, 0), (1, 1)), (0, 1)),
        (((float("nan"), 0), (1, 1)), (1, 1)),
        (((0, 0),) * 65, (1,) * 65),
    ):
        with pytest.raises(LimbError):
            tube(points, widths)
