"""Two adjacent gestures, and a motion with contacts, for the limb motion tests."""

from __future__ import annotations

from dataclasses import replace

from srstudio.limbs import HUMAN, ArmProfile, Frame, Quaternion, Vec3
from srstudio.limbs.motion import Action, Contact, Motion, MotionStyle, TransformKey, TransformTrack


def gestures(side='right', moving=False):
    root = TransformTrack.constant(Frame())
    if moving:
        root = TransformTrack(
            tuple(
                TransformKey(t, Frame(Vec3(0.08 * t, 0, 0), Quaternion.axis_angle(Vec3(0, 0, 1), 0.04 * t)))
                for t in (0, 2, 4, 5)
            ),
            interpolation='continuous',
        )
    return Motion(
        ArmProfile(side=side),
        HUMAN,
        (Action('point', duration=2, style=MotionStyle(asymmetry=0.2)), Action('present', start=2, duration=2)),
        root=root,
    )


def contact_motion():
    source = Motion(ArmProfile(), HUMAN, (Action('rest', duration=2), Action('rest', start=2, duration=2)))
    frame = source.sample(0).hand.frame
    target = TransformTrack(
        (
            TransformKey(0, frame, velocity=Vec3(0.02, 0, 0)),
            TransformKey(4, Frame(frame.origin + Vec3(0.08, 0, 0), frame.rotation), velocity=Vec3(0.02, 0, 0)),
        ),
        interpolation='continuous',
    )
    return replace(source, contacts=(Contact('first', 0.5, 1.5, target), Contact('second', 2.5, 3.5, target)))
