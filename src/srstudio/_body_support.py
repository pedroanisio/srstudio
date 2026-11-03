"""Bounded public support geometry over the body's existing hull and margin solver."""

from __future__ import annotations

from collections.abc import Sequence

from . import _body_solve as solver
from . import checks
from ._body_types import BodyProfile, fail, frame
from .limbs.errors import LimbError
from .limbs.math3d import Frame, Vec3

Point = tuple[float, float]
Polygon = tuple[Point, ...]
MAX_POINTS = 4096


def _coordinate(value: object, path: str) -> float:
    if not checks.number(value) or not -1000 <= value <= 1000:
        raise fail(path, value, 'a finite nonboolean coordinate within +/-1000 meters', 'body.support')
    return float(value)


def _points(points: Sequence[Point]) -> Polygon:
    if type(points) not in (tuple, list) or not 3 <= len(points) <= MAX_POINTS:
        raise fail('support.points', points, f'a list or tuple of 3..{MAX_POINTS} x/z pairs', 'body.support')
    result = []
    for i, point in enumerate(points):
        path = f'support.points[{i}]'
        if type(point) not in (tuple, list) or len(point) != 2:
            raise fail(path, point, 'an x/z pair in meters', 'body.support')
        result.append((_coordinate(point[0], path + '.x'), _coordinate(point[1], path + '.z')))
    return tuple(result)


def support_hull(points: Sequence[Point]) -> Polygon:
    """Return the counterclockwise convex x/z hull, beginning at its lexicographic minimum.

    Input order and duplicate points do not affect the result. At most 4096
    finite points in the +/-1000 meter body workspace are accepted. A collinear
    or otherwise degenerate support set raises BodyError.
    """
    polygon = solver.hull(_points(points))
    if len(polygon) < 3:
        raise fail('support.points', points, 'at least three noncollinear support points', 'body.support')
    return polygon


def _polygon(points: Sequence[Point]) -> Polygon:
    polygon = _points(points)
    expected = support_hull(polygon)
    if len(expected) != len(polygon):
        raise fail('support.polygon', polygon, 'unique vertices of a strictly convex hull', 'body.support')
    start = expected.index(polygon[0])
    if polygon != expected[start:] + expected[:start]:
        raise fail(
            'support.polygon',
            polygon,
            'counterclockwise convex vertices without a repeated closing point',
            'body.support',
        )
    return polygon


def support_margin(polygon: Sequence[Point], point: Vec3) -> float:
    """Minimum signed edge clearance of point's x/z projection, in meters.

    Positive is inside, zero is on an edge, negative is outside. This is the
    body's half-plane margin, not Euclidean distance to the nearest corner.
    Polygon vertices must be a counterclockwise convex hull.
    """
    boundary = _polygon(polygon)
    if type(point) is not Vec3:
        raise fail('support.point', point, 'a world-space Vec3 in meters', 'body.support')
    for name in ('x', 'y', 'z'):
        _coordinate(getattr(point, name), 'support.point.' + name)
    return solver.margin(boundary, point)


def support_area(polygon: Sequence[Point]) -> float:
    """Area in square meters of a counterclockwise convex support hull."""
    boundary = _polygon(polygon)
    x, z = boundary[0]
    return (
        sum(
            (a[0] - x) * (b[1] - z) - (b[0] - x) * (a[1] - z)
            for a, b in zip(boundary, (*boundary[1:], boundary[0]), strict=True)
        )
        / 2
    )


def support_footprint(sole: Frame, profile: BodyProfile) -> tuple[Vec3, ...]:
    """Four world-space sole corners on y=0, from the profile's full width, heel and toe.

    The sole must be a yaw-only ground frame. This describes a planted sole;
    it does not infer contact from an airborne or tilted foot.
    """
    if type(profile) is not BodyProfile:
        raise fail('support.profile', profile, 'an immutable BodyProfile', 'body.support')
    profile.__post_init__()
    try:
        frame(sole, 'support.sole', ground=True)
        return solver.footprint(sole, profile)
    except LimbError as error:
        raise fail('support.sole', sole, 'a finite yaw-only ground frame', 'body.support') from error
