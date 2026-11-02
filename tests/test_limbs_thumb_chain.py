"""The HUMAN thumb exposes the rig's three articulated segments without rewriting saved anatomy."""

from dataclasses import replace

import pytest

from srstudio.limbs import HUMAN, MITTEN, ArmProfile, Frame, HandControl, LimbError, hand_pose
from srstudio.limbs.motion import Motion
from srstudio.limbs.serialization import motion_dict, parse_motion


def test_human_thumb_has_three_bones_in_the_canonical_ratio_and_preserves_total_reach():
    thumb = HUMAN.digits[0]
    assert thumb.name == 'thumb'
    assert thumb.lengths == pytest.approx((0.12, 0.10, 0.08))
    assert sum(thumb.lengths) == pytest.approx(0.3)
    control = HandControl(joints=(('thumb', (0.2, 0.4, 0.6)),), opposition=0.5)
    right = hand_pose(HUMAN, control, Frame()).digit('thumb')
    left = hand_pose(HUMAN, control, Frame(), side='left').digit('thumb')
    assert len(right.points) == 4
    assert all(a.mirror().distance(b) < 1e-9 for a, b in zip(right.points, left.points, strict=True))
    assert [a.distance(b) for a, b in zip(right.points, right.points[1:], strict=False)] == pytest.approx(thumb.lengths)


def test_saved_two_segment_thumb_is_still_explicit_anatomy():
    old = replace(HUMAN, digits=(replace(HUMAN.digits[0], lengths=(0.17, 0.13)), *HUMAN.digits[1:]))
    restored = parse_motion(motion_dict(Motion(ArmProfile(), old)))
    assert restored.hand == old
    assert len(restored.sample(0).hand.digit('thumb').points) == 3
    assert len(MITTEN.digits[0].lengths) == 2


def test_human_thumb_refuses_legacy_joint_count_instead_of_truncating():
    with pytest.raises(LimbError, match='topology'):
        hand_pose(HUMAN, HandControl(joints=(('thumb', (0.2, 0.4)),)), Frame())
