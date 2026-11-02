"""Body proportions are authored independently instead of inferred from pelvis width."""

from dataclasses import replace

import pytest

from srstudio import body
from srstudio.limbs import Frame, Quaternion, Vec3


def authored(profile):
    return body.BodyScore(
        1,
        (body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),),
        (body.FootAnchor('left', Frame(Vec3(-0.12, 0, 0))), body.FootAnchor('right', Frame(Vec3(0.12, 0, 0)))),
        profile=profile,
    )


def test_shoulder_width_is_independent_and_rotates_with_the_torso():
    profile = body.BodyProfile(hip_width=0.24, shoulder_width=0.52, foot_width=0.1)
    score = authored(profile)
    yaw = Quaternion.axis_angle(Vec3(0, 1, 0), 0.25)
    score = replace(score, roots=(replace(score.roots[0], torso=yaw),))
    pose = body.compile_body(score).sample(0.5)
    left, right = pose.shoulders
    assert left.origin.distance(right.origin) == pytest.approx(0.52)
    assert pose.torso.inverse_point(left.origin).x == pytest.approx(-0.26)
    assert pose.legs[0].hip.distance(pose.legs[1].hip) == pytest.approx(0.24)
    footprint = body.support_footprint(pose.legs[0].sole, profile)
    assert footprint[0].distance(footprint[1]) == pytest.approx(0.1)
    assert body.support_area(tuple((p.x, p.z) for p in footprint)) == pytest.approx(0.024)


def test_omitted_shoulder_width_retains_legacy_proportions():
    profile = body.BodyProfile(hip_width=0.3)
    assert profile.shoulder_width is None
    pose = body.compile_body(authored(profile)).sample(0)
    assert pose.shoulders[0].origin.distance(pose.shoulders[1].origin) == pytest.approx(0.45)


def test_canonical_mannequin_shoulders_are_not_derived_from_hip_spacing():
    # srlocations' neutral 1.75 m mannequin: clavicle offsets 0.02 + 0.11 of height; hips +/-0.05.
    height = 1.75
    profile = body.BodyProfile(hip_width=2 * 0.05 * height, shoulder_width=2 * (0.02 + 0.11) * height)
    pose = body.compile_body(authored(profile)).sample(0)
    assert pose.shoulders[0].origin.distance(pose.shoulders[1].origin) == pytest.approx(0.455)
    assert pose.legs[0].hip.distance(pose.legs[1].hip) == pytest.approx(0.175)
    assert profile.foot_width == 0.12


@pytest.mark.parametrize('width', [0, -1, 2.1, True, float('nan'), '0.3'])
def test_shoulder_width_has_typed_bounds(width):
    with pytest.raises(body.BodyError):
        body.BodyProfile(shoulder_width=width)


def test_data_only_body_input_preserves_explicit_shoulder_width():
    data = {
        'schema': 'srstudio.body/1.1.0',
        'duration': 1,
        'roots': [{'time': 0, 'root': {'origin': [0, -0.88, 0]}}],
        'stance': [{'side': side, 'frame': {'origin': [x, 0, 0]}} for side, x in [('left', -0.12), ('right', 0.12)]],
        'profile': {'shoulder_width': 0.52, 'foot_width': 0.1},
    }
    pose = body.compile_body(body.parse_body(data)).sample(0)
    assert pose.shoulders[0].origin.distance(pose.shoulders[1].origin) == pytest.approx(0.52)
    data['schema'] = 'srstudio.body/1.0.0'
    with pytest.raises(body.BodyError, match='1.1.0'):
        body.parse_body(data)
