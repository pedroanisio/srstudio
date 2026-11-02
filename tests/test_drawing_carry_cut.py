"""Nothing hangs from the frontal native shoulder across a camera cut."""

import importlib
import math
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_body')


def _position(time):
    from examples.drawing_proof import sample

    return np.array(sample(time).view.position, dtype=float)


def test_declared_camera_cuts_are_the_only_view_discontinuities(example):
    steps = [i / 480 for i in range(6 * 480 + 1)]
    jumps = [b for a, b in zip(steps, steps[1:], strict=False) if np.linalg.norm(_position(b) - _position(a)) > 5]
    assert tuple(jumps) == example.CAMERA_CUTS


def test_candidate_releases_every_shoulder_attachment_before_each_camera_cut(example):
    carry = example.candidate_carry()
    for attachment in carry.attachments:
        for cut in example.CAMERA_CUTS:
            assert not attachment.attach <= cut <= attachment.release
    example.check_cuts(carry)


def test_a_carry_held_across_a_camera_cut_is_refused(example):
    from examples.acting_continuity import carry_motion

    with pytest.raises(ValueError, match='cup is attached to the frontal shoulder across the camera cut at 4'):
        example.check_cuts(carry_motion())


def test_retimed_carry_keeps_the_authored_grip_path_and_pickup_pose(example):
    from examples.acting_continuity import carry_motion

    original, carry = carry_motion(), example.candidate_carry()
    path, retimed = original.contacts[0].target.keys, carry.contacts[0].target.keys
    assert [key.time for key in retimed] == [1.2, 2.0, 2.8, 3.6]
    assert [key.frame for key in retimed] == [key.frame for key in path]
    attachment = carry.attachments[0]
    assert (attachment.attach, attachment.release) == (1.2, 3.6)
    assert carry.prop_frame('cup', 3.6) == original.prop_frame('cup', 1.2)
    speed = [
        carry.sample(t / 48).hand.frame.origin.distance(carry.sample((t + 1) / 48).hand.frame.origin) * 48
        for t in range(24, 287)
    ]
    peak = [
        original.sample(t / 48).hand.frame.origin.distance(original.sample((t + 1) / 48).hand.frame.origin) * 48
        for t in range(24, 287)
    ]
    assert max(speed) <= max(peak)


@pytest.mark.parametrize('cut', [4])
def test_world_props_stay_put_while_the_frontal_trunk_turns_at_the_cut(example, cut):
    from examples.drawing_attached import shoulder_frame

    before, after = cut - 1e-3, cut
    meshes = [{mesh.material: mesh.vertices for mesh in example.candidate_mesh(t)} for t in (before, after)]
    for material in ('cup', 'coffee'):
        assert np.array_equal(meshes[0][material], meshes[1][material])
    turn = shoulder_frame(after, placement=example.body_transform(after)).origin.distance(
        shoulder_frame(before, placement=example.body_transform(before)).origin
    )
    assert turn > 10  # The shoulder really turns with the trunk here; only empty hands may follow it.
    assert math.isfinite(turn)


def test_cup_rests_in_world_space_outside_the_retimed_contact(example):
    for times in ((0, 0.6, 1.2), (3.6, 4, 5, 6)):
        cups = [{mesh.material: mesh.vertices for mesh in example.candidate_mesh(t)} for t in times]
        for material in ('cup', 'coffee'):
            assert all(np.array_equal(cups[0][material], cup[material]) for cup in cups[1:])


@pytest.mark.parametrize('yaw', [-35.0, 0.0, 20.0])
def test_each_foot_drawing_points_its_toes_along_the_solved_sole(example, yaw):
    from dataclasses import replace

    from srstudio.limbs import Frame, Quaternion, Vec3

    leg = example.body_plan().sample(1.0).legs[0]
    turned = replace(leg, sole=Frame(leg.sole.origin, Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(yaw))))
    transform = example.foot_transform(turned, 1.0)
    assert transform.rotation == pytest.approx((0, yaw, 0), abs=1e-9)
    rotation = Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(transform.rotation[1]))
    toes = rotation.rotate(Vec3(0, 0, 1))  # The frontal paw drawing's card normal.
    forward = turned.sole.rotation.rotate(Vec3(0, 0, 1))
    assert (toes.x, toes.y, toes.z) == pytest.approx((forward.x, forward.y, forward.z), abs=1e-12)


def test_a_tilted_sole_has_no_frontal_paw_drawing_and_is_refused(example):
    from dataclasses import replace

    from srstudio.limbs import Frame, Quaternion, Vec3

    leg = example.body_plan().sample(1.0).legs[0]
    tilted = replace(leg, sole=Frame(leg.sole.origin, Quaternion.axis_angle(Vec3(1, 0, 0), 0.2)))
    with pytest.raises(ValueError, match='level sole'):
        example.foot_transform(tilted, 1.0)


def test_a_shared_grip_path_with_authored_velocities_is_not_silently_retimed(example, monkeypatch):
    from dataclasses import replace

    from examples.acting_continuity import carry_motion

    from srstudio.limbs import Vec3

    source = carry_motion()
    contact = source.contacts[0]
    keys = (replace(contact.target.keys[0], velocity=Vec3(0, 0, 0)), *contact.target.keys[1:])
    moving = replace(source, contacts=(replace(contact, target=replace(contact.target, keys=keys)),))
    monkeypatch.setattr(example, 'carry_motion', lambda: moving)
    with pytest.raises(ValueError, match='four positional grip keys'):
        example.candidate_carry.__wrapped__()
