"""Public support geometry for skeleton adapters shares the body's support convention."""

import math
from dataclasses import replace

import pytest

from srstudio import body
from srstudio.limbs import Frame, Quaternion, Vec3


def test_public_footprint_hull_margin_and_area_agree_with_body_samples():
    profile = body.BodyProfile()
    stance = tuple(body.FootAnchor(side, Frame(Vec3(x, 0, 0))) for side, x in (('left', -0.12), ('right', 0.12)))
    plan = body.compile_body(body.BodyScore(1, (body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),), stance))
    pose = plan.sample(0)
    points = [p for foot in stance for p in body.support_footprint(foot.frame, profile)]
    polygon = body.support_hull([(p.x, p.z) for p in points])
    assert polygon == pose.support_polygon
    assert body.support_margin(polygon, pose.center_of_mass) == pytest.approx(pose.support_margin)
    assert body.support_area(polygon) == pytest.approx(0.36 * 0.24)
    assert body.support_margin(polygon, Vec3(1, 0, 0)) < 0


def test_public_support_geometry_is_rigid_transform_invariant():
    profile = replace(body.BodyProfile(), foot_width=0.2, heel=0.1, toe=0.3)
    transform = Frame(Vec3(2, 0, -3), Quaternion.axis_angle(Vec3(0, 1, 0), math.pi / 3))
    footprint = body.support_footprint(transform, profile)
    polygon = body.support_hull([(p.x, p.z) for p in footprint])
    assert body.support_area(polygon) == pytest.approx(0.08)
    assert body.support_margin(polygon, transform.point(Vec3(0, 0, 0.1))) == pytest.approx(0.1)
    assert body.support_hull(tuple(reversed(polygon)) + (polygon[0],)) == polygon


def test_support_area_keeps_small_feet_precise_near_workspace_edges():
    polygon = body.support_hull(((999, 999), (999.01, 999), (999.01, 999.01), (999, 999.01)))
    assert body.support_area(polygon) == pytest.approx(0.0001, rel=1e-9, abs=1e-13)


@pytest.mark.parametrize(
    'points',
    [
        None,
        'abc',
        [(0, 0)],
        [(0, 0), (1, 0), (2, 0)],
        [(0, 0), (1, 0), (0, True)],
        [(0, 0), (1, 0), (0, float('nan'))],
        [(0, 0), (1, 0), (0, 1001)],
        [(0, 0)] * 4097,
        [(0, 0), (1, 0), (0,)],
    ],
)
def test_public_hull_refuses_unbounded_or_degenerate_input_with_repair_fields(points):
    with pytest.raises(body.BodyError) as caught:
        body.support_hull(points)
    detail = caught.value.to_dict()
    assert detail['code'] == 'body.support'
    assert detail['path'].startswith('support.') and detail['expected'] and detail['remedy']


@pytest.mark.parametrize(
    'polygon',
    [
        (),
        ((0, 0), (1, 0)),
        ((0, 0), (0, 1), (1, 0)),
        ((0, 0), (1, 0), (0.2, 0.2), (0, 1)),
        ((0, 0), (1, 0), (0, 1), (0, 0)),
    ],
)
def test_public_polygon_operations_require_an_ordered_counterclockwise_convex_hull(polygon):
    for operation, args in ((body.support_area, (polygon,)), (body.support_margin, (polygon, Vec3()))):
        with pytest.raises(body.BodyError):
            operation(*args)


def test_public_footprint_refuses_invalid_profiles_and_non_ground_soles():
    profile = body.BodyProfile()
    for sole, shape in (
        (None, profile),
        (Frame(Vec3(0, 1, 0)), profile),
        (Frame(rotation=Quaternion.axis_angle(Vec3(1, 0, 0), 0.1)), profile),
        (Frame(), {}),
    ):
        with pytest.raises(body.BodyError):
            body.support_footprint(sole, shape)
    polygon = body.support_hull(((0, 0), (1, 0), (0, 1)))
    with pytest.raises(body.BodyError):
        body.support_margin(polygon, (0, 0, 0))
