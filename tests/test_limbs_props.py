"""Shared prop anchors coordinate two arms and expose physical clearance failures."""

from dataclasses import replace

import pytest

from srstudio.limbs import HUMAN, ArmProfile, Frame, LimbError, Vec3
from srstudio.limbs.motion import Action, Motion, TransformKey, TransformTrack
from srstudio.limbs.props import Anchor, Coordination, Prop, Sphere, bind, clearance


def fixture():
    right = Motion(ArmProfile(shoulder=Vec3(-0.6, 0, 0)), HUMAN, (Action("grasp", duration=2),))
    left = Motion(ArmProfile(shoulder=Vec3(0.6, 0, 0), side="left"), HUMAN, (Action("grasp", duration=2),))
    a, b = right.sample(1).hand.frame, left.sample(1).hand.frame
    prop = Prop(
        "tray",
        TransformTrack((TransformKey(0, Frame()), TransformKey(2, Frame(Vec3(0, 0.04, 0))))),
        (Anchor("right", a), Anchor("left", b)),
    )
    return right, left, prop


def test_two_hands_hold_named_anchors_on_one_moving_prop_under_random_access():
    right, left, prop = fixture()
    pair = Coordination(bind(right, prop, "right", 0.8, 1.3), bind(left, prop, "left", 0.8, 1.3), (prop,))
    for t in (1.3, 0.8, 1.1, 0.95):
        sample = pair.sample(t)
        assert sample.right.hand.frame.origin.distance(prop.frame("right", t).origin) < 1e-8
        assert sample.left.hand.frame.origin.distance(prop.frame("left", t).origin) < 1e-8
        assert len(sample.props) == 1
        assert pair.sample(t) == sample


def test_clearance_reports_penetration_and_strict_mode_rejects_it():
    right, _, _ = fixture()
    sample = right.sample(1)
    obstacle = Sphere("torso", sample.arm.elbow, 0.2)
    diagnostics = clearance(sample, right.arm.width / 2, (obstacle,))
    assert diagnostics and diagnostics[0].code == "collision"
    assert diagnostics[0].residual > 0
    with pytest.raises(LimbError, match="torso"):
        clearance(sample, right.arm.width / 2, (obstacle,), strict=True)
    assert not clearance(sample, 0.1, (Sphere("far", Vec3(20, 0, 0), 1),))


def test_shared_prop_contracts_reject_duplicate_names_and_unresolved_anchors():
    right, left, prop = fixture()
    with pytest.raises(LimbError, match="anchor"):
        bind(right, prop, "missing", 0.8, 1.3)
    with pytest.raises(LimbError):
        replace(prop, anchors=(prop.anchors[0], prop.anchors[0]))
    with pytest.raises(LimbError):
        Coordination(left, right)
    with pytest.raises(LimbError):
        Sphere("bad", Vec3(), -1)
    with pytest.raises(LimbError):
        Coordination(right, left, (prop, prop))
