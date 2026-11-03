"""Moving contact acquisition, orientation, residual checks and attachment lifetimes."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import TYPE_CHECKING

from ._motion_gestures import _GOALS
from ._motion_interpolation import smooth, tangent_weights
from .constraints import hand_pose, reach
from .errors import Diagnostic, LimbError
from .math3d import Frame, Quaternion, Vec3, number
from .model import HandControl, HandPose

if TYPE_CHECKING:
    from .motion import Action, Contact, Motion


def request(motion: Motion, contact: Contact, time: float, control: HandControl) -> tuple[Vec3, Quaternion]:
    frame = contact.frame(time)
    if contact.digit is None:
        return frame.origin, frame.rotation
    fingers = replace(control, wrist_flex=0, wrist_deviation=0, forearm_twist=0)
    offset = hand_pose(motion.hand, fingers, Frame(), side=motion.arm.side).digit(contact.digit).points[-1]
    return frame.origin - frame.rotation.rotate(offset), frame.rotation


def position(motion: Motion, action: Action, time: float, fallback: Vec3) -> Vec3:
    contacts = [c for c in motion.contacts if action.start < c.start < c.end < action.end]
    active = next((c for c in contacts if c.start <= time <= c.end), None)
    if active:
        return motion._contact_request(active, time, motion._request(time)[1])[0]
    if not contacts:
        return fallback
    previous = next((c for c in reversed(contacts) if c.end < time), None)
    following = next((c for c in contacts if c.start > time), None)
    start = previous.end if previous else action.start
    end = following.start if following else action.end
    span = end - start
    u = (time - start) / span

    def position(contact: Contact | None, at: float) -> Vec3:
        if contact:
            return motion._contact_request(contact, at, motion._request(at)[1])[0]
        return motion._relative(_GOALS['rest'], at)

    def velocity(contact: Contact | None, at: float) -> Vec3:
        h = min(1e-4, span * 1e-3)
        lo, hi = max(0.0, at - h), at + h
        return (position(contact, hi) - position(contact, lo)) / (hi - lo)

    ta, tb = tangent_weights(u)
    return (
        position(previous, start).lerp(position(following, end), smooth(u))
        + (velocity(previous, start) * ta + velocity(following, end) * tb) * span
    )


def resolve(
    motion: Motion, time: float, goal: Vec3, control: HandControl, action: Action | None
) -> tuple[Vec3, Quaternion | None, bool, Contact | None]:
    """Resolve wrist position/orientation and active contact before the final skeletal solve."""
    orientation: Quaternion | None = None
    local_orientation = False
    active: Contact | None = None
    if action is not None:
        contacts = [c for c in motion.contacts if action.start < c.start < c.end < action.end]
        active = next((c for c in contacts if c.start <= time <= c.end), None)
        if active:
            goal, orientation = motion._contact_request(active, time, control)
        elif contacts:
            previous = next((c for c in reversed(contacts) if c.end < time), None)
            following = next((c for c in contacts if c.start > time), None)
            start_time = previous.end if previous else action.start
            end_time = following.start if following else action.end

            def endpoint(contact: Contact | None, at: float) -> tuple[Vec3, Quaternion]:
                if contact:
                    return motion._contact_request(contact, at, motion._request(at)[1])
                rest = motion._relative(_GOALS["rest"], at)
                profile = replace(motion.arm, shoulder=motion.root.sample(at).point(motion.arm.shoulder))
                endpoint_pole = motion._pole(action, at, rest)
                resting = reach(profile, rest, pole=endpoint_pole, policy=motion.reach_policy)
                return rest, resting.frame.rotation

            a, qa = endpoint(previous, start_time)
            b, qb = endpoint(following, end_time)
            span = end_time - start_time
            u = (time - start_time) / span
            weight = smooth(u)

            # Quintic Hermite coefficients for matching endpoint angular velocity.
            ta, tb = tangent_weights(u)
            if action.pole is not None:
                # Blend wrist offsets in the moving arm frame, so the pole's turn does not become wrist twist.
                def relative_rotation(at: float, target: Vec3, rotation: Quaternion) -> Quaternion:
                    profile = replace(motion.arm, shoulder=motion.root.sample(at).point(motion.arm.shoulder))
                    arm = reach(profile, target, pole=motion._pole(action, at, target), policy=motion.reach_policy)
                    return arm.frame.rotation.inverse() * rotation

                qa = relative_rotation(start_time, a, qa)
                qb = relative_rotation(end_time, b, qb)
                local_orientation = True
            goal, orientation = motion._contact_position(action, time, goal), qa.slerp(qb, weight)

            def angular_velocity(contact: Contact | None, at: float) -> Vec3:
                h = min(1e-4, span * 1e-3)
                lo, hi = max(0.0, at - h), at + h
                p, q0 = endpoint(contact, lo)
                q, q1 = endpoint(contact, hi)
                if action.pole is not None:
                    q0, q1 = relative_rotation(lo, p, q0), relative_rotation(hi, q, q1)
                delta = q0.inverse() * q1
                if delta.w < 0:
                    delta = -delta
                vector = Vec3(delta.x, delta.y, delta.z)
                if vector.length < 1e-12:
                    return Vec3()
                return vector.unit() * (2 * math.atan2(vector.length, delta.w) / (hi - lo))

            turn = (angular_velocity(previous, start_time) * ta + angular_velocity(following, end_time) * tb) * span
            if turn.length > 1e-12:
                orientation = orientation * Quaternion.axis_angle(turn, turn.length)
    return goal, orientation, local_orientation, active


def diagnostics(active: Contact | None, hand: HandPose, time: float) -> tuple[Diagnostic, ...]:
    """Check the solved hand against its actual world contact anchor."""
    diagnostics: tuple[Diagnostic, ...] = ()
    if active:
        at = hand.frame.origin if active.digit is None else hand.digit(active.digit).points[-1]
        error = at.distance(active.frame(time).origin)
        if error > 1e-6:
            raise LimbError(f"contact {active.name} has residual {error:g}", code="contact", residual=error)
        diagnostics = (Diagnostic("contact", active.name, error),)
    return diagnostics


def prop_frame(motion: Motion, name: str, time: float) -> Frame:
    number(time, "prop time")
    for attachment in motion.attachments:
        if attachment.name == name:
            if time < attachment.attach:
                return attachment.initial
            return motion.sample(min(time, attachment.release)).hand.frame.compose(attachment.offset)
    raise LimbError(f"unknown attached prop {name!r}")
