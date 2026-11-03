"""The body against the floor (ADR 0194): where the mass is, what the planted feet hold up, and a foot laid flat.

The centre of mass weighs each segment of the skeleton by its share of body mass (Winter, *Biomechanics and Motor
Control of Human Movement*, 4th ed., table 4.1) at the middle of the bone, the trunk split evenly over its four spine
bones; a joint a character omits is left out and the rest renormalised. The shares are a person's, so on a cartoon with
a large head they are an estimate.

The support of the planted feet is the skeleton bridge's (``sk.to_body_pose``): which soles lie flat on the floor,
``body``'s public footprint under each on the character's ``sk.body_profile``, and ``body``'s hull of them. How far a
point stands inside it is ``body.support_margin``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from . import body
from . import skeleton as sk
from ._retarget_feet import has_leg, reach
from ._retarget_pose import Tally
from .limbs.math3d import Frame, Quaternion, Vec3

SIDES = ("left", "right")
UP_AXIS = Vec3(0.0, 1.0, 0.0)
FORWARD = Vec3(0.0, 0.0, 1.0)
_TRUNK = 0.497 / 4
# (from, to, share): ``to`` None is the joint itself; "tip" the bone's end.
MASSES: tuple[tuple[str, str | None, float], ...] = (
    ("head", "tip", 0.081),
    ("hips", "spine", _TRUNK),
    ("spine", "chest", _TRUNK),
    ("chest", "upper_chest", _TRUNK),
    ("upper_chest", "neck", _TRUNK),
    *(
        (f"{side}_{a}", f"{side}_{b}" if b else None, share)
        for side in SIDES
        for a, b, share in (
            ("upper_arm", "lower_arm", 0.028),
            ("lower_arm", "hand", 0.016),
            ("hand", None, 0.006),
            ("upper_leg", "lower_leg", 0.100),
            ("lower_leg", "foot", 0.0465),
            ("foot", "toes", 0.0145),
        )
    ),
)


def yaw(angle: float) -> Quaternion:
    """A turn about the vertical, positive toward the right."""
    return Quaternion.axis_angle(UP_AXIS, angle)


def heading(rotation: Quaternion) -> float:
    """The turn about the vertical that faces ``rotation``'s forward, read on the floor."""
    ahead = rotation.rotate(FORWARD)
    return math.atan2(ahead.x, ahead.z)


def centre_of_mass(profile: sk.SkeletonProfile, frames: Mapping[str, Frame], crown: Vec3) -> Vec3:
    """The weighted middle of the character's segments, from its world frames and the head's crown."""
    total, weight = Vec3(), 0.0
    for start, end, share in MASSES:
        if start not in frames:
            continue
        a = frames[start].origin
        if end == "tip":
            b = crown
        elif end is None or end not in frames:
            b = a
        else:
            b = frames[end].origin
        total = total + (a + b) * (share / 2)
        weight += share
    return total * (1 / weight)


def body_of(profile: sk.SkeletonProfile, pose: sk.SkeletonPose) -> tuple[dict[str, Frame], Vec3]:
    """The pose's world frames and its centre of mass."""
    frames = sk.world(profile, pose)
    crown = frames["head"].point(profile.tip("head") or Vec3())
    return frames, centre_of_mass(profile, frames, crown)


def margin(polygon: tuple[tuple[float, float], ...], point: Vec3) -> float:
    """How far ``point`` stands inside the support ``polygon`` on the floor, in metres, negative outside: body's
    signed margin."""
    return body.support_margin(polygon, point)


def sole(profile: sk.SkeletonProfile) -> tuple[float, float, float]:
    """A foot's footprint about the point under its ankle: half its width, the heel behind, the toes ahead. The
    sizes are the skeleton's sole (``sk.body_profile``: the joint table's width and heel scaled with the foot)."""
    body = sk.body_profile(profile)
    return body.foot_width / 2, body.heel, body.toe


def support(
    profile: sk.SkeletonProfile, pose: sk.SkeletonPose, floor_y: float, feet: Iterable[str]
) -> tuple[tuple[tuple[float, float], ...], tuple[str, ...]] | None:
    """The convex support, on the floor's (x, z), of those of the named sides' feet that lie flat as ``pose`` stands
    on the floor at ``floor_y``, with the sides it counts; ``None`` when none does. Flatness, footprints and hull are
    the skeleton bridge's (``sk.to_body_pose``), with the pose set down so the floor is y=0."""
    root = pose.root
    grounded = sk.SkeletonPose(Frame(root.origin - Vec3(0.0, floor_y, 0.0), root.rotation), pose.values)
    try:
        whole = sk.to_body_pose(profile, grounded)
    except sk.SkeletonBridgeError as error:
        if error.code != "skeleton.support":
            raise
        return None  # no foot lies flat on the floor
    down = {leg.side for leg in whole.legs if leg.planted}
    named = tuple(side for side in SIDES if side in set(feet) and side in down)
    if not named:
        return None
    if set(named) == down:
        return whole.support_polygon, named
    return sk.to_body_pose(profile, grounded, planted=named).support_polygon, named


def toes_offset(profile: sk.SkeletonProfile, side: str) -> Vec3:
    """Where the ball of the foot sits on the ankle, in the foot's frame: the toes' joint, or the ankle itself."""
    name = f"{side}_toes"
    return profile.offset(name) if profile.has(name) else Vec3()


def flat_ankle(
    profile: sk.SkeletonProfile, side: str, ball: tuple[float, float], heading_rad: float, floor_y: float
) -> Vec3:
    """Where the ankle stands when the foot lies flat on the floor at ``floor_y``, its ball at ``ball`` (x, z) and
    its toes toward ``heading_rad``."""
    toes = toes_offset(profile, side)
    reach_back = yaw(heading_rad).rotate(Vec3(toes.x, 0.0, toes.z))
    return Vec3(ball[0] - reach_back.x, floor_y - profile.length("ankle"), ball[1] - reach_back.z)


def ball_of(profile: sk.SkeletonProfile, frames: Mapping[str, Frame], side: str) -> Vec3:
    name = f"{side}_toes"
    return frames[name].origin if name in frames else frames[f"{side}_foot"].origin


def floor_of(profile: sk.SkeletonProfile, pose: sk.SkeletonPose) -> float:
    """The floor a pose stands on: under its lower ankle by the ankle's height (y points down)."""
    frames = sk.world(profile, pose)
    sides = [s for s in SIDES if f"{s}_foot" in frames] or []
    if not sides:
        return 0.0
    return max(frames[f"{s}_foot"].origin.y for s in sides) + profile.length("ankle")


def lay(
    profile: sk.SkeletonProfile,
    values: Mapping[str, float],
    root: Frame,
    side: str,
    ankle: Vec3,
    heading_rad: float,
    tally: Tally,
    time_s: float,
) -> dict[str, float]:
    """``values`` with one leg solved so its foot lies flat toward ``heading_rad`` with the ankle at ``ankle``."""
    out = reach(profile, values, root, side, ankle, tally, time_s, turn=yaw(heading_rad))
    if profile.has(f"{side}_toes"):
        out[f"{side}_toes.up_down"] = 0.0
    return out


def legs(profile: sk.SkeletonProfile) -> tuple[str, ...]:
    return tuple(side for side in SIDES if has_leg(profile, side))
