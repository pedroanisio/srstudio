"""Gesture timing, retargeting and prop contact must remain exact under random-access sampling."""

import math
from dataclasses import replace

import pytest

from srstudio.limbs.math3d import Frame, Quaternion, Vec3
from srstudio.limbs.model import HUMAN, ArmProfile, LimbError
from srstudio.limbs.motion import (
    ACTIONS,
    Action,
    Attachment,
    Contact,
    Motion,
    MotionStyle,
    Target,
    TransformKey,
    TransformTrack,
    WordRef,
)


@pytest.mark.parametrize("name", ACTIONS)
def test_actions_have_preparation_stroke_hold_and_recovery_and_preserve_anatomy(name):
    action = Action(name, start=0.5, duration=2)
    motion = Motion(ArmProfile(), HUMAN, (action,))
    before = motion.sample(0)
    during = motion.sample(1.5)
    after = motion.sample(3)
    assert before.arm.wrist == after.arm.wrist
    if name == "rest":
        assert during.arm.wrist == before.arm.wrist
    else:
        assert during.arm.wrist != before.arm.wrist or during.control != before.control
    for t in (0, 0.5, 0.8, 1.3, 1.5, 2.0, 2.5, 3):
        sample = motion.sample(t)
        assert sample.arm.shoulder.distance(sample.arm.elbow) == pytest.approx(motion.arm.upper)
        assert sample.arm.elbow.distance(sample.arm.wrist) == pytest.approx(motion.arm.forearm)


def test_sampling_backwards_or_after_seeking_is_identical_to_sequential_playback():
    m = Motion(ArmProfile(), HUMAN, (Action("wave", 0, 2, style=MotionStyle(overshoot=0.1, settling=0.15)),))
    expected = {i: m.sample(i / 24) for i in range(72)}
    for i in reversed(range(72)):
        assert m.sample(i / 24) == expected[i]


def test_relative_actions_retarget_by_proportions_and_world_targets_do_not_move():
    action = Action("point", 0, 2, target=Target(Vec3(0.6, 0.3, 0.1)))
    a = Motion(ArmProfile(), HUMAN, (action,))
    b = a.retarget(ArmProfile(upper=2, forearm=1.8))
    assert b.sample(1).arm.wrist.distance(a.sample(1).arm.wrist * 2) < 1e-8
    target = Target(Vec3(0.8, 0.8, 0.1), space="world")
    a = Motion(ArmProfile(), HUMAN, (replace(action, target=target),))
    b = a.retarget(ArmProfile(upper=1.3, forearm=1.2))
    assert a.sample(1).arm.wrist.distance(b.sample(1).arm.wrist) < 1e-8


def test_word_reference_is_an_unambiguous_occurrence_and_aligns_the_stroke():
    from srstudio.timeline import Take

    take = Take(
        "01",
        "actor",
        "wide",
        "No, no.",
        3,
        2,
        words=({"text": "No,", "start": 0.1, "end": 0.4}, {"text": "no.", "start": 0.8, "end": 1.0}),
    )
    ref = WordRef("01", 1)
    action = Action.on_word("point", ref, [take], duration=1)
    assert action.stroke_at == pytest.approx(3.8)
    for bad in (WordRef("missing", 0), WordRef("01", 5)):
        with pytest.raises(LimbError, match="word"):
            Action.on_word("point", bad, [take], duration=1)


def test_fingertip_contact_locks_to_a_moving_surface_without_sliding():
    base = Motion(ArmProfile(), HUMAN, (Action("press", 0, 2),))
    sample = base.sample(1)
    tip = sample.hand.digit("index").points[-1]
    surface = TransformTrack(
        (
            TransformKey(0, Frame(tip, sample.hand.frame.rotation)),
            TransformKey(2, Frame(tip + Vec3(0.1, 0, 0), sample.hand.frame.rotation)),
        )
    )
    contact = Contact("button", 0.8, 1.3, surface, digit="index")
    motion = replace(base, contacts=(contact,))
    for t in (0.8, 0.95, 1.1, 1.3):
        pose = motion.sample(t)
        assert pose.hand.digit("index").points[-1].distance(surface.sample(t).origin) < 1e-8
        assert pose.contacts[0].residual < 1e-8


def test_attachment_follows_hand_then_remains_at_release_pose_independent_of_seek():
    base = Motion(ArmProfile(), HUMAN, (Action("grasp", 0, 3),))
    offset = Frame(Vec3(0, 0.3, 0))
    initial = base.sample(1.2).hand.frame.compose(offset)
    attachment = Attachment("cup", 1.2, 2.0, initial, offset)
    motion = replace(base, attachments=(attachment,))
    assert motion.prop_frame("cup", 0) == initial
    assert motion.prop_frame("cup", 1.5) == motion.sample(1.5).hand.frame.compose(offset)
    released = motion.prop_frame("cup", 2.0)
    assert motion.prop_frame("cup", 3.0) == released
    assert motion.prop_frame("cup", 2.0) == released


def test_contacts_and_attachments_reject_conflicts_and_teleporting_acquisition():
    m = Motion(ArmProfile(), HUMAN, (Action("grasp", 0, 3),))
    target = TransformTrack.constant(Frame(Vec3(0, 1, 0)))
    c = Contact("desk", 1, 2, target)
    with pytest.raises(LimbError, match="overlap"):
        replace(m, contacts=(c, replace(c, name="face", start=1.5)))
    with pytest.raises(LimbError, match="acquisition"):
        replace(m, attachments=(Attachment("cup", 1, 2, Frame(Vec3(50, 50, 0))),))


def test_transform_tracks_use_shortest_rotation_and_reject_duplicate_or_unordered_times():
    a = Frame(Vec3(), Quaternion())
    b = Frame(Vec3(2, 0, 0), Quaternion.axis_angle(Vec3(0, 1, 0), 1))
    track = TransformTrack((TransformKey(0, a), TransformKey(2, b)))
    assert track.sample(1).origin == Vec3(1, 0, 0)
    assert track.sample(-1) == a and track.sample(3) == b
    with pytest.raises(LimbError):
        TransformTrack((TransformKey(1, a), TransformKey(1, b)))


def test_individual_joint_overrides_blend_from_anatomical_rest_instead_of_being_refused():
    from srstudio.limbs.model import HandControl

    control = HandControl(joints=(("index", (0.3, 0.4, 0.2)),))
    m = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2, control=control),))
    assert dict(m.sample(1).control.joints)["index"] == pytest.approx((0.3, 0.4, 0.2))
    assert all(0 <= v <= 1.3 for v in dict(m.sample(0.5).control.joints)["index"])


def test_successive_contacts_transition_from_the_previous_contact_without_jumping():
    base = Motion(ArmProfile(), HUMAN, (Action("type", 0, 2),))
    first = base.sample(0.5).hand.frame
    second = base.sample(1.1).hand.frame
    contacts = (
        Contact("key-a", 0.4, 0.6, TransformTrack.constant(first)),
        Contact("key-b", 1, 1.2, TransformTrack.constant(second)),
    )
    m = replace(base, contacts=contacts)
    for boundary in (0.4, 0.6, 1, 1.2):
        a = m.sample(boundary - 1e-7).arm.wrist
        b = m.sample(boundary + 1e-7).arm.wrist
        assert a.distance(b) < 1e-5


@pytest.mark.parametrize("kwargs", [{"name": "dance"}, {"duration": 0}, {"start": -1}, {"duration": float("nan")}])
def test_bad_actions_fail_before_any_scene_is_mutated(kwargs):
    with pytest.raises(LimbError):
        Action(**{"name": "point", "start": 0, "duration": 1, **kwargs})


def test_contact_transitions_keep_the_authored_elbow_pole_at_rest_endpoints():
    action = Action("grasp", duration=3, pole=Vec3(0, 1, 0))
    base = Motion(ArmProfile(), HUMAN, (action,))
    grip = base.sample(1.2).hand.frame
    m = replace(base, contacts=(Contact("hold", 1.2, 2.1, TransformTrack.constant(grip)),))
    for i in range(73):
        sample = m.sample(i / 24)
        assert abs(sample.control.wrist_deviation) <= 0.8


@pytest.mark.parametrize("u", [0.9999999999999999, 0.999999997, 1 - 2**-40, 1e-17, 0.5])
def test_minimum_jerk_easing_stays_inside_its_unit_range_at_rounding_limits(u):
    from srstudio.limbs.motion import smooth

    assert 0.0 <= smooth(u) <= 1.0
    assert smooth(0) == 0.0 and smooth(1) == 1.0


@pytest.mark.parametrize("time", [0.7 + 0.1 + 0.1 + 0.1, 1 - 2**-52, 2 - 2**-51])
def test_transform_tracks_sample_accumulated_float_times_near_a_key(time):
    a = Frame(Vec3(), Quaternion())
    b = Frame(Vec3(1, 0, 0), Quaternion.axis_angle(Vec3(0, 0, 1), 1))
    c = Frame(Vec3(2, 0, 0), Quaternion.axis_angle(Vec3(0, 0, 1), 2))
    track = TransformTrack((TransformKey(0, a), TransformKey(1, b), TransformKey(2, c)))
    sampled = track.sample(time)
    nearest = b if time < 1.5 else c
    assert sampled.origin.distance(nearest.origin) < 1e-9


def _grasp_with_contact(start, end):
    base = Motion(ArmProfile(), HUMAN, (Action("grasp", 0.5, 2.0),))
    grip = base.sample(1.5).hand.frame
    return replace(base, contacts=(Contact("grip", start, end, TransformTrack.constant(grip)),))


@pytest.mark.parametrize(("start", "end"), [(0.5, 1.0), (2.0, 2.5), (0.5, 2.5)])
def test_contacts_touching_an_action_edge_are_refused_instead_of_teleporting_the_wrist(start, end):
    with pytest.raises(LimbError, match="transition"):
        _grasp_with_contact(start, end)


def test_adjacent_contacts_are_refused_because_the_hand_cannot_travel_between_them():
    base = Motion(ArmProfile(), HUMAN, (Action("type", 0, 2),))
    first = TransformTrack.constant(base.sample(0.5).hand.frame)
    second = TransformTrack.constant(base.sample(1.1).hand.frame)
    with pytest.raises(LimbError, match="transition"):
        replace(base, contacts=(Contact("key-a", 0.4, 0.8, first), Contact("key-b", 0.8, 1.2, second)))


def test_wrist_steps_stay_continuous_across_both_action_edges_of_a_contact():
    import statistics

    m = _grasp_with_contact(0.75, 2.25)
    wrists = [m.sample(i / 24).arm.wrist for i in range(73)]
    steps = [a.distance(b) for a, b in zip(wrists, wrists[1:], strict=False)]
    moving = statistics.median(s for s in steps if s > 1e-9)
    assert max(steps) <= 3 * moving
    for edge in (0.5, 0.75, 2.25, 2.5):
        coarse = m.sample(edge - 1e-3).arm.wrist.distance(m.sample(edge + 1e-3).arm.wrist)
        fine = m.sample(edge - 1e-4).arm.wrist.distance(m.sample(edge + 1e-4).arm.wrist)
        # A continuous pose moves less over a shorter interval; a jump does not shrink with the interval.
        assert fine <= coarse * 0.2 + 1e-9


@pytest.mark.parametrize("duration", [0.4, 2.0])
def test_settling_wobble_fades_out_by_the_end_of_the_hold(duration):
    action = Action("point", 0, duration, style=MotionStyle(settling=1.0))
    m = Motion(ArmProfile(), HUMAN, (action,))
    end_hold = action.start + (action.preparation + action.stroke + action.hold) * action.duration
    before, after = m.sample(end_hold - 1e-9), m.sample(end_hold + 1e-9)
    assert (before.phase, after.phase) == ("hold", "recovery")
    assert before.arm.wrist.distance(after.arm.wrist) < 1e-6
    still = Motion(ArmProfile(), HUMAN, (replace(action, style=MotionStyle()),))
    middle = action.stroke_at + math.pi / 36  # the wobble's first peak
    # The wobble still shapes the hold; it only ends with it.
    assert m.sample(middle).arm.wrist.distance(still.sample(middle).arm.wrist) > 1e-4


def test_settling_without_a_hold_samples_the_instantaneous_hold_without_dividing_by_zero():
    action = Action("point", 0, 2, hold=0, style=MotionStyle(settling=1.0))
    sample = Motion(ArmProfile(), HUMAN, (action,)).sample(action.stroke_at)
    assert sample.phase == "hold"
