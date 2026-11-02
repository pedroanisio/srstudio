"""A dance on the floor: planted feet held, the body kept over them, and dancers in a formation (ADR 0194).

``dance.sample`` and ``dance_pose`` say what a body does; this module puts it on a floor, for any style:

    toon = skeleton.preset("cartoon")
    run = dance_floor.perform(dance.phrases()["class-groove"], toon, Groove(122.65))
    run.pose(1.0)                                  # a pose at a second of the song, feet held
    run.slip(50), run.balance(50)                  # how far a planted foot slid; the frames off balance
    frames = dance_floor.plant(toon, sampled)      # the same pass on any DanceFrame sequence a style already has
    dance_floor.ground(toon, pose, ("left", "right"))  # one pose, both feet laid flat on the floor

**Planted feet.** A foot is planted while its frame says so (``planted``; both feet on a ``seat`` frame, which rests
them on the floor). It lands where the free pose puts it at the first moment of the plant, laid flat on the floor and
turned the way it pointed; from then its ball stays on that spot. When the body turns on the floor (a frame's
``floor.turn``) a planted foot pivots on its ball by the same turn, as a dancer's does; otherwise it does not turn.
The leg is solved onto it by ``retarget``'s leg solve. In the ``BLEND_S`` either side of a plant the foot eases from
its free path onto the spot and back, so it never jumps, and a free foot never goes through the floor.

**Balance.** The hips shift on the floor so that the centre of mass stands over the feet that carry the body. At
each key (a phrase's keys, and each change of the planted feet) the least shift is solved that puts the centre of
mass ``aim`` inside the support of the feet planted on both sides of the key, and between keys the shift moves on the
later key's ease. So the weight moves onto the standing foot before the other lifts, and stays there until it lands.
:meth:`Performance.balance` reports every frame whose centre of mass is not ``margin_m`` inside its support, as a
:class:`BalanceFinding`; ``strict`` refuses the dance with a :class:`BalanceError`. A frame in the air, or seated,
is not checked.

**Ensemble.** :func:`ensemble` gives each :class:`Dancer` its own performance of one dance from its :class:`Spot` on
the floor, with its own delay in beats (a canon), plus a small timing and size variation drawn from ``seed``.
"""

from __future__ import annotations

import math
import random
from bisect import bisect_right
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType

from . import checks
from . import skeleton as sk
from ._dance_model import DanceError, Move, Routine
from ._dance_phrase import Floor, Phrase, ease
from ._dance_sample import MAX_FRAMES, DanceFrame, sample
from ._floor_body import (
    ball_of,
    body_of,
    flat_ankle,
    floor_of,
    heading,
    lay,
    legs,
    margin,
    sole,
    support,
    toes_offset,
    yaw,
)
from ._retarget_errors import LimitBreach
from ._retarget_feet import BLEND_S, reach
from ._retarget_pose import Tally
from .dance_pose import dance_pose
from .limbs.math3d import Frame, Vec3
from .music import Groove

__all__ = [
    "AIM_SHARE",
    "BLEND_S",
    "FORMATIONS",
    "MAX_DANCERS",
    "MAX_JITTER_BEATS",
    "MAX_SIZE_VARIATION",
    "SCAN_PER_BEAT",
    "STANCE_BEND",
    "STANCE_TURNOUT",
    "STANCE_WIDTH",
    "BalanceError",
    "BalanceFinding",
    "Dancer",
    "FloorError",
    "FloorFrame",
    "FloorLimitError",
    "Performance",
    "Slip",
    "Spot",
    "centre_of_mass",
    "ensemble",
    "formation",
    "ground",
    "perform",
    "plant",
    "knee_bend",
    "seated",
    "stance",
]

SCAN_PER_BEAT = 48  # where a performance looks for plants: every sixteenth lands on this grid
SHIFT_PASSES = 8  # each pass moves the hips by what the centre of mass misses; legs carry about a third back
AIM_SHARE = 0.25  # the shift aims this share of a foot's width inside the support, past the margin
MAX_SHIFT = 0.5  # hip heights the balance may shift the hips
REACH_SHARE = 0.995  # a held leg straightens to this share of its length before the hips sink
MAX_SINK = 0.3  # hip heights the hips may sink to keep a held foot in reach
EPSILON_S = 1e-6
MAX_DANCERS = 16
MAX_JITTER_BEATS = 0.04
MAX_SIZE_VARIATION = 0.06
FORMATIONS = ("line", "wedge")
MAX_FINDINGS = 256
STANCE_WIDTH = 0.5  # hip heights between the ankles of the groove stance: a wide base
STANCE_BEND = 0.55  # radians the knees bend in it, as a dance study measures a knee
STANCE_TURNOUT = 0.25  # radians each foot's toes turn out
MAX_STANCE_WIDTH = 1.0
MAX_STANCE_BEND = 1.2
MAX_STANCE_TURNOUT = 0.6
STANCE_DROP = 0.7  # hip heights the stance's search may lower the hips; deeper than any bend it allows
STANCE_HALVINGS = 40
STANCE_REACH = 1e-4  # hip heights a stance's ankle may miss its spot


class FloorError(DanceError):
    """A dance that cannot be put on the floor as given: an unknown input, a bound broken."""


class FloorLimitError(FloorError):
    """Holding a planted foot would turn a leg's joint past its limit (and ``clamp`` is off)."""

    def __init__(self, breaches: tuple[LimitBreach, ...], count: int) -> None:
        listed = ", ".join(f"{b.key} {b.value:.3f} at {b.time_s:.3f}s" for b in breaches[:8])
        super().__init__(f"{count} leg value(s) pass their limits: {listed}", code="dance.floor.limit", path="legs")
        self.breaches = breaches
        self.count = count


@dataclass(frozen=True)
class BalanceFinding:
    """A frame whose centre of mass stands ``margin_m`` inside the support of ``planted`` (negative: outside)."""

    time: float
    margin_m: float
    planted: frozenset[str]


class BalanceError(FloorError):
    """A dance whose centre of mass leaves its support, refused at the strict setting."""

    def __init__(self, findings: tuple[BalanceFinding, ...], count: int, profile: str) -> None:
        worst = min(findings, key=lambda f: f.margin_m)
        super().__init__(
            f"{profile}: {count} frame(s) off balance, worst {worst.margin_m * 1000:.1f} mm at {worst.time:.3f}s",
            code="dance.floor.balance",
            path="balance",
            actual=count,
        )
        self.findings = findings
        self.count = count


@dataclass(frozen=True)
class Spot:
    """A place on the floor in metres (``x`` right, ``z`` forward of the floor's middle) and the way the dancer faces,
    in radians, positive toward the right."""

    x: float = 0.0
    z: float = 0.0
    facing: float = 0.0

    def __post_init__(self) -> None:
        for name, bound in (("x", 100.0), ("z", 100.0), ("facing", 4 * math.pi)):
            value = getattr(self, name)
            if not (checks.number(value) and abs(value) <= bound):
                raise FloorError(f"spot {name} {value!r} lies in -{bound:g}..{bound:g}", path=f"spot.{name}")

    def frame(self) -> Frame:
        return Frame(Vec3(self.x, 0.0, self.z), yaw(self.facing))


CENTRE = Spot()  # the floor's middle, facing forward


@dataclass(frozen=True)
class FloorFrame:
    """One moment on the floor: the pose, the feet that carry it, whether it is in the air, how it is held up, its
    centre of mass, and how far that stands inside the planted feet (None when nothing on the floor carries it)."""

    time: float
    pose: sk.SkeletonPose
    planted: frozenset[str]
    airborne: bool
    support: str
    com: Vec3
    margin_m: float | None
    dropped: frozenset[str]


@dataclass(frozen=True)
class Slip:
    """The farthest a planted foot's ball moved from where it landed, and the farthest its ankle moved while the
    body did not turn on the floor (in a turn the heel swings round the ball, by design), in metres."""

    ball_m: float
    ankle_m: float


@dataclass(frozen=True)
class _Hold:
    side: str
    start: float
    end: float
    ball: tuple[float, float]
    heading: float
    turn: float  # the floor turn when the foot landed: the foot pivots by what the body turns since


@dataclass(frozen=True)
class _Key:
    time: float
    ease: str
    feet: frozenset[str]  # the sides the shift keeps the body over; empty: hold the shift before


def _sides(frame: DanceFrame) -> frozenset[str]:
    """The sides a frame stands on: its planted feet, or both on a seat."""
    if frame.support == "seat":
        return frozenset(("left", "right"))
    return frozenset(foot.split("_")[0] for foot in frame.planted)


def _check_profile(profile: object) -> sk.SkeletonProfile:
    if not isinstance(profile, sk.SkeletonProfile):
        raise FloorError(f"a dance is put on a skeleton.SkeletonProfile, not {type(profile).__name__}", path="profile")
    return profile


def _check_flag(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise FloorError(f"{name} {value!r} is True or False", path=name)
    return value


class _Pass:
    """The planted-feet and balance pass for one character over one timeline (see the module's notes)."""

    def __init__(
        self,
        profile: sk.SkeletonProfile,
        base: sk.SkeletonPose,
        frame_at: Callable[[float], DanceFrame],
        scan: Sequence[tuple[float, DanceFrame]],
        keys: Sequence[tuple[float, str]],
        *,
        clamp: bool,
        balance: bool,
        margin_m: float,
    ) -> None:
        self.profile, self.base, self.frame_at = profile, base, frame_at
        self.clamp, self.margin_m = clamp, margin_m
        self.legs = legs(profile)
        self.reach_m = {
            side: profile.offset(f"{side}_lower_leg").length + profile.offset(f"{side}_foot").length
            for side in self.legs
        }
        self.floor_y = floor_of(profile, base)
        self.holds = self._holds(scan)
        self.keys: list[_Key] = []
        self.shifts: list[Vec3] = []
        if balance:
            self._balance(keys)

    # --- plants ---------------------------------------------------------------------------------------------------

    def _holds(self, scan: Sequence[tuple[float, DanceFrame]]) -> dict[str, list[_Hold]]:
        out: dict[str, list[_Hold]] = {side: [] for side in self.legs}
        for side in self.legs:
            i = 0
            while i < len(scan):  # one pass over the scan per side
                if side not in _sides(scan[i][1]):
                    i += 1
                    continue
                first = i
                while i + 1 < len(scan) and side in _sides(scan[i + 1][1]):
                    i += 1
                t0, frame = scan[first]
                free = sk.world(self.profile, self._free(frame, Vec3())[0])
                ball = ball_of(self.profile, free, side)
                out[side].append(
                    _Hold(
                        side, t0, scan[i][0], (ball.x, ball.z), heading(free[f"{side}_foot"].rotation), frame.floor.turn
                    )
                )
                i += 1
        return out

    def _hold(self, side: str, t: float) -> tuple[_Hold, float] | None:
        """The hold that reaches ``t`` and its weight: 1 inside it, easing to 0 over ``BLEND_S`` outside."""
        best: tuple[_Hold, float] | None = None
        holds = self.holds.get(side, [])
        i = bisect_right([h.start for h in holds], t + EPSILON_S)
        for hold in holds[max(0, i - 2) : i + 1]:
            if hold.start - EPSILON_S <= t <= hold.end + EPSILON_S:
                return hold, 1.0
            gap = hold.start - t if t < hold.start else t - hold.end
            if gap < BLEND_S and (best is None or 1 - gap / BLEND_S > best[1]):
                u = 1 - gap / BLEND_S
                best = (hold, u * u * (3 - 2 * u))
        return best

    def _ankle(self, hold: _Hold, frame: DanceFrame) -> tuple[Vec3, float]:
        turned = hold.heading + (frame.floor.turn - hold.turn)
        return flat_ankle(self.profile, hold.side, hold.ball, turned, self.floor_y), turned

    # --- one pose -------------------------------------------------------------------------------------------------

    def _free(self, frame: DanceFrame, shift: Vec3) -> tuple[sk.SkeletonPose, frozenset[str]]:
        danced = dance_pose(self.profile, frame, base=self.base, clamp=self.clamp)
        root = danced.pose.root
        return sk.SkeletonPose(Frame(root.origin + shift, root.rotation), danced.pose.values), danced.dropped

    def solve(self, frame: DanceFrame, t: float, shift: Vec3, tally: Tally) -> tuple[sk.SkeletonPose, frozenset[str]]:
        """The pose at ``t``: the free pose shifted, each held foot solved onto its spot, each free foot over the
        floor."""
        free, dropped = self._free(frame, shift)
        values, root = free.as_dict(), free.root
        world = sk.world(self.profile, free)
        standing = _sides(frame)
        held: dict[str, tuple[Vec3, float, float]] = {}
        for side in self.legs:
            found = self._hold(side, t)
            if found is not None and (found[1] < 1 or side in standing):
                hold, weight = found
                ankle, turned = self._ankle(hold, frame)
                foot = world[f"{side}_foot"]
                target = ankle if weight >= 1 else self._above(foot.origin.lerp(ankle, weight), foot, world, side)
                held[side] = (target, turned, weight)
        drop = self._sink(world, held)
        if drop > 0:
            root = Frame(root.origin + Vec3(0.0, drop, 0.0), root.rotation)
            world = sk.world(self.profile, sk.pose(self.profile, values, root=root))
        for side in self.legs:
            foot = world[f"{side}_foot"]
            if side in held:
                target, turned, weight = held[side]
                if weight >= 1:
                    values = lay(self.profile, values, root, side, target, turned, tally, t)
                    continue
                turn = foot.rotation.slerp(yaw(turned), weight)
                values = reach(self.profile, values, root, side, target, tally, t, turn=turn)
                continue
            above = self._above(foot.origin, foot, world, side)
            if above.y < foot.origin.y - 1e-12:
                values = reach(self.profile, values, root, side, above, tally, t)
        return sk.pose(self.profile, values, root=root), dropped

    def _sink(self, world: Mapping[str, Frame], held: Mapping[str, tuple[Vec3, float, float]]) -> float:
        """How far the hips sink (metres, y down) so every held foot's ankle is within ``REACH_SHARE`` of its leg's
        full length, as a dancer bends the standing knee rather than drag the far foot; at most ``MAX_SINK`` hip
        heights."""
        drop = 0.0
        for side, (target, _, _) in held.items():
            hip = world[f"{side}_upper_leg"].origin
            full = REACH_SHARE * self.reach_m[side]
            across = math.hypot(target.x - hip.x, target.z - hip.z)
            below = math.sqrt(full * full - across * across) if across < full else 0.0
            drop = max(drop, target.y - below - hip.y)
        return min(drop, MAX_SINK * self.profile.pelvis_height)

    def _above(self, target: Vec3, foot: Frame, world: Mapping[str, Frame], side: str) -> Vec3:
        """``target`` raised, if need be, so neither the sole under the ankle nor the toes' tip go through the
        floor (y points down)."""
        low = target.y + self.profile.length("ankle")
        name = f"{side}_toes"
        if name in world:
            tip = world[name].point(self.profile.tip(name) or Vec3())
            low = max(low, target.y + (tip.y - foot.origin.y))
        return Vec3(target.x, target.y - max(0.0, low - self.floor_y), target.z)

    # --- balance --------------------------------------------------------------------------------------------------

    def _balance(self, keys: Sequence[tuple[float, str]]) -> None:
        height = self.profile.pelvis_height
        aim = self.margin_m + AIM_SHARE * 2 * sole(self.profile)[0]
        last = Vec3()
        for t, kind in keys:  # bounded by the keys the caller built, each solved in SHIFT_PASSES
            frame = self.frame_at(t)
            feet = _sides(frame)
            around = _sides(self.frame_at(t - EPSILON_S)) & feet & _sides(self.frame_at(t + EPSILON_S))
            if not around:
                around = feet & (_sides(self.frame_at(t - EPSILON_S)) | _sides(self.frame_at(t + EPSILON_S))) or feet
            if frame.support != "feet":
                around = frozenset()
            around = around & set(self.legs)
            shift = Vec3() if around else last
            for _ in range(SHIFT_PASSES if around else 0):
                pose, _ = self.solve(frame, t, shift, Tally(True))
                frames, com = body_of(self.profile, pose)
                polygon = support(self.profile, frames, around)
                if margin(polygon, com) >= aim:
                    break
                goal = _toward(polygon, com, aim)
                shift = shift + Vec3(goal[0] - com.x, 0.0, goal[1] - com.z)
                size = math.hypot(shift.x, shift.z)
                if size > MAX_SHIFT * height:
                    shift = shift * (MAX_SHIFT * height / size)
            self.keys.append(_Key(t, kind, around))
            self.shifts.append(shift)
            last = shift

    def shift(self, t: float) -> Vec3:
        if not self.keys:
            return Vec3()
        i = bisect_right([k.time for k in self.keys], t)
        if i == 0:
            return self.shifts[0]
        if i == len(self.keys):
            return self.shifts[-1]
        a, b = self.keys[i - 1], self.keys[i]
        return self.shifts[i - 1].lerp(self.shifts[i], ease(b.ease, (t - a.time) / (b.time - a.time)))

    def at(self, t: float, frame: DanceFrame) -> FloorFrame:
        tally = Tally(self.clamp)
        pose, dropped = self.solve(frame, t, self.shift(t), tally)
        if tally.breach_count:
            raise FloorLimitError(tuple(tally.breaches), tally.breach_count)
        frames, com = body_of(self.profile, pose)
        feet = _sides(frame) & set(self.legs)
        found = None
        if frame.support == "feet" and feet:
            found = margin(support(self.profile, frames, feet), com)
        planted = frozenset(f"{side}_foot" for side in feet)
        return FloorFrame(t, pose, planted, frame.airborne, frame.support, com, found, dropped)


def _toward(polygon: tuple[tuple[float, float], ...], point: Vec3, aim: float) -> tuple[float, float]:
    """The nearest point to ``point`` on the line to the polygon's middle that stands ``aim`` inside; the middle
    itself when nothing does. Bisection, 30 halvings."""
    middle = (sum(p[0] for p in polygon) / len(polygon), sum(p[1] for p in polygon) / len(polygon))
    centre = Vec3(middle[0], 0.0, middle[1])
    if margin(polygon, centre) < aim:
        return middle
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if margin(polygon, point.lerp(centre, mid)) >= aim:
            hi = mid
        else:
            lo = mid
    goal = point.lerp(centre, hi)
    return goal.x, goal.z


def centre_of_mass(profile: sk.SkeletonProfile, pose: sk.SkeletonPose) -> Vec3:
    """A pose's centre of mass in world metres, from the segment shares of a person (see ``_floor_body``)."""
    return body_of(_check_profile(profile), pose)[1]


def _margin(profile: sk.SkeletonProfile, margin_m: float | None) -> float:
    if margin_m is None:
        return min(0.005, sole(profile)[0] / 2)
    if not (checks.number(margin_m) and 0 <= margin_m <= 0.1):
        raise FloorError(f"margin_m {margin_m!r} lies in 0..0.1 metres", path="margin_m")
    return float(margin_m)


def _base(profile: sk.SkeletonProfile, base: object, spot: object) -> sk.SkeletonPose:
    if not isinstance(spot, Spot):
        raise FloorError(f"spot is a dance_floor.Spot, not {type(spot).__name__}", path="spot")
    if base is None:
        base = sk.rest_pose(profile)
    if not isinstance(base, sk.SkeletonPose):
        raise FloorError(f"base is a skeleton.SkeletonPose, not {type(base).__name__}", path="base")
    return sk.SkeletonPose(spot.frame().compose(base.root), base.values)


def plant(
    profile: sk.SkeletonProfile,
    frames: Sequence[DanceFrame],
    *,
    base: sk.SkeletonPose | None = None,
    spot: Spot = CENTRE,
    clamp: bool = False,
    balance: bool = True,
    margin_m: float | None = None,
) -> tuple[FloorFrame, ...]:
    """Any style's dance frames on the floor, in order: each frame danced from ``base`` (the rest pose by default;
    a seated base keeps its feet where it rests them) at ``spot``, planted feet held, the body over them when
    ``balance``. ``frames`` is what :func:`dance.frames` gives: times strictly rising, at most ``MAX_FRAMES``."""
    profile = _check_profile(profile)
    if not (isinstance(frames, Sequence) and 1 <= len(frames) <= MAX_FRAMES):
        raise FloorError(f"frames are a sequence of 1..{MAX_FRAMES} DanceFrame", path="frames")
    if not all(isinstance(f, DanceFrame) for f in frames):
        raise FloorError("every frame is a dance.DanceFrame", path="frames")
    times = [f.time for f in frames]
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise FloorError("frames are in strictly rising time", path="frames")

    def at(t: float) -> DanceFrame:
        return frames[max(0, bisect_right(times, t) - 1)]

    keys = [(times[0], "smooth")]
    for i in range(1, len(frames)):
        if _sides(frames[i]) != _sides(frames[i - 1]):
            keys += [(times[i - 1], "smooth"), (times[i], "smooth")]
    keys.append((times[-1], "smooth"))
    ordered = sorted(dict(keys).items())
    run = _Pass(
        profile,
        _base(profile, base, spot),
        at,
        [(f.time, f) for f in frames],
        ordered,
        clamp=_check_flag(clamp, "clamp"),
        balance=_check_flag(balance, "balance"),
        margin_m=_margin(profile, margin_m),
    )
    return tuple(run.at(f.time, f) for f in frames)


def ground(
    profile: sk.SkeletonProfile,
    pose: sk.SkeletonPose,
    feet: Sequence[str] = ("left", "right"),
    *,
    floor_y: float = 0.0,
    clamp: bool = False,
) -> sk.SkeletonPose:
    """``pose`` with each named side's foot laid flat on the floor at ``floor_y`` under where its ball is, turned the
    way it points; the rest of the pose unchanged."""
    profile = _check_profile(profile)
    if not isinstance(pose, sk.SkeletonPose):
        raise FloorError(f"pose is a skeleton.SkeletonPose, not {type(pose).__name__}", path="pose")
    if not (isinstance(feet, (tuple, list)) and set(feet) <= {"left", "right"} and len(set(feet)) == len(feet)):
        raise FloorError(f"feet {feet!r} names left and right at most once each", path="feet")
    if not checks.number(floor_y):
        raise FloorError(f"floor_y {floor_y!r} is a finite number of metres", path="floor_y")
    tally = Tally(_check_flag(clamp, "clamp"))
    world = sk.world(profile, pose)
    values = pose.as_dict()
    for side in feet:
        if side not in legs(profile):
            continue
        ball = ball_of(profile, world, side)
        turned = heading(world[f"{side}_foot"].rotation)
        ankle = flat_ankle(profile, side, (ball.x, ball.z), turned, float(floor_y))
        values = lay(profile, values, pose.root, side, ankle, turned, tally, 0.0)
    if tally.breach_count:
        raise FloorLimitError(tuple(tally.breaches), tally.breach_count)
    return sk.pose(profile, values, root=pose.root)


def seated(profile: sk.SkeletonProfile) -> sk.SkeletonPose:
    """A base pose sitting on a seat at knee height: thighs level and forward, shins straight down, feet flat on the
    floor where the rest pose stands. Seat moves danced from it keep the feet where it rests them."""
    profile = _check_profile(profile)
    rest = sk.rest_pose(profile)
    values = rest.as_dict()
    for side in legs(profile):
        values[f"{side}_upper_leg.front_back"] = -math.pi / 2
        values[f"{side}_lower_leg.stretch"] = -math.pi / 2
    folded = sk.pose(profile, values, root=rest.root)
    rise = floor_of(profile, rest) - floor_of(profile, folded)
    return sk.SkeletonPose(Frame(rest.root.origin + Vec3(0.0, rise, 0.0), rest.root.rotation), folded.values)


def knee_bend(profile: sk.SkeletonProfile, pose: sk.SkeletonPose) -> float:
    """How far the knees bend in ``pose``, radians, both legs' mean: the turn of the shin off the line of the thigh,
    measured from the hip, knee and ankle joints as a dance study measures a dancer's (0 for a straight leg)."""
    world = sk.world(_check_profile(profile), pose)
    bends = []
    for side in legs(profile):
        hip, knee = world[f"{side}_upper_leg"].origin, world[f"{side}_lower_leg"].origin
        a, b = hip - knee, world[f"{side}_foot"].origin - knee
        cos = (a.x * b.x + a.y * b.y + a.z * b.z) / max(a.length * b.length, 1e-12)
        bends.append(math.pi - math.acos(max(-1.0, min(1.0, cos))))
    return sum(bends) / len(bends) if bends else 0.0


def stance(
    profile: sk.SkeletonProfile,
    *,
    width: float = STANCE_WIDTH,
    bend: float = STANCE_BEND,
    turnout: float = STANCE_TURNOUT,
    clamp: bool = False,
) -> sk.SkeletonPose:
    """A base pose for a groove: the ankles ``width`` hip heights apart across the floor, each foot flat and turned
    out ``turnout`` radians, and the hips lowered until the knees bend ``bend`` radians (:func:`knee_bend`), the legs
    solved by the leg solve. A dance from it keeps that base: its knees fold further as its hips drop."""
    profile = _check_profile(profile)
    for name, value, high in (
        ("width", width, MAX_STANCE_WIDTH),
        ("bend", bend, MAX_STANCE_BEND),
        ("turnout", turnout, MAX_STANCE_TURNOUT),
    ):
        if not (checks.number(value) and 0 <= value <= high):
            raise FloorError(f"{name} {value!r} lies in 0..{high}", path=name)
    rest = sk.rest_pose(profile)
    floor, height = floor_of(profile, rest), profile.pelvis_height
    rest_world = sk.world(profile, rest)

    ankles = {
        side: Vec3(
            rest.root.origin.x + (1.0 if side == "right" else -1.0) * width * height / 2,
            floor - profile.length("ankle"),
            rest_world[f"{side}_foot"].origin.z,
        )
        for side in legs(profile)
    }

    def at(drop: float, tally: Tally) -> sk.SkeletonPose:
        root = Frame(rest.root.origin + Vec3(0.0, drop, 0.0), rest.root.rotation)
        values = rest.as_dict()
        for side, ankle in ankles.items():
            values = lay(profile, values, root, side, ankle, (1.0 if side == "right" else -1.0) * turnout, tally, 0.0)
        return sk.pose(profile, values, root=root)

    low, high = 0.0, STANCE_DROP * height
    for _ in range(STANCE_HALVINGS):  # the bend grows as the hips drop
        middle = (low + high) / 2
        if knee_bend(profile, at(middle, Tally(True))) < bend:
            low = middle
        else:
            high = middle
    tally = Tally(_check_flag(clamp, "clamp"))
    pose = at(high, tally)
    if tally.breach_count:
        raise FloorLimitError(tuple(tally.breaches), tally.breach_count)
    world = sk.world(profile, pose)
    if any(world[f"{side}_foot"].origin.distance(ankle) > STANCE_REACH * height for side, ankle in ankles.items()):
        raise FloorError(
            f"knees bent {bend!r} do not reach feet {width!r} hip heights apart; bend them further", path="bend"
        )
    return pose


# --- a dance performed on the floor -----------------------------------------------------------------------------


def _length_beats(source: Phrase | Routine) -> float:
    if isinstance(source, Phrase):
        return float(source.beats)
    return float(source.track_bars * source.beats_per_bar)


def _key_beats(source: Phrase | Routine) -> list[tuple[float, str]]:
    """The beats the balance is solved on: each key of each phrase danced, and where each move's entry opens."""
    if isinstance(source, Phrase):
        return [(k.beat, k.ease) for k in source.keys]
    out: list[tuple[float, str]] = []
    per_bar = source.beats_per_bar
    for e in source.entries:  # bounded by the routine's entries and beats
        start = e.start_bar * per_bar
        if isinstance(e.move, Move):
            out.append((float(start), "smooth"))
            continue
        for r in range((e.end_bar - e.start_bar) * per_bar // e.move.beats):
            out.extend((start + r * e.move.beats + k.beat, k.ease) for k in e.move.keys)
    return out


class Performance:
    """One dancer's dance on the floor, sampled at any second of the song. Built by :func:`perform`."""

    def __init__(
        self,
        source: Phrase | Routine,
        profile: sk.SkeletonProfile,
        groove: Groove,
        *,
        spot: Spot,
        base: sk.SkeletonPose | None,
        delay_s: float,
        size: float,
        clamp: bool,
        balance: bool,
        margin_m: float | None,
    ) -> None:
        self.source, self.profile, self.groove, self.spot = source, profile, groove, spot
        self.base = base if base is not None else sk.rest_pose(profile)
        self.delay_s, self.size = delay_s, size
        self.start_s = groove.offset + delay_s
        self.end_s = self.start_s + _length_beats(source) * groove.beat
        step = groove.beat / SCAN_PER_BEAT
        count = round((self.end_s - self.start_s) / step) + 1
        if count > MAX_FRAMES:
            raise FloorError(f"{count} scan steps exceed {MAX_FRAMES}; shorten the dance", path="source")
        scan = [(self.start_s + n * step, self.frame(self.start_s + n * step)) for n in range(count)]
        keys = [(self.start_s + beat * groove.beat, kind) for beat, kind in _key_beats(source)]
        for (t0, f0), (t1, f1) in zip(scan, scan[1:], strict=False):
            if _sides(f0) != _sides(f1) and not any(t0 - step - EPSILON_S <= t <= t1 + EPSILON_S for t, _ in keys):
                keys += [(t0, "smooth"), (t1, "smooth")]
        self.margin_m = _margin(profile, margin_m)
        self._pass = _Pass(
            profile,
            _base(profile, base, spot),
            self.frame,
            scan,
            sorted(dict(sorted(keys)).items()),
            clamp=clamp,
            balance=balance,
            margin_m=self.margin_m,
        )
        self._frames: dict[int, tuple[FloorFrame, ...]] = {}

    @property
    def floor_y(self) -> float:
        """The floor this dancer stands on, in world metres (y points down)."""
        return self._pass.floor_y

    def frame(self, t: float) -> DanceFrame:
        """The dance frame this dancer dances at the song's second ``t``."""
        found = sample(self.source, self.groove, t - self.delay_s)
        if self.size != 1.0:
            found = replace(found, joints=MappingProxyType({k: v * self.size for k, v in found.joints.items()}))
        return replace(found, time=t)

    def sample(self, t: float) -> FloorFrame:
        if not checks.number(t):
            raise FloorError(f"time {t!r} is a finite number of seconds", path="t")
        return self._pass.at(float(t), self.frame(float(t)))

    def pose(self, t: float) -> sk.SkeletonPose:
        return self.sample(t).pose

    def frames(self, fps: int) -> tuple[FloorFrame, ...]:
        """The performance at ``fps`` pictures a second from its start to its end, both included."""
        if type(fps) is not int or not 1 <= fps <= 240:
            raise FloorError(f"fps {fps!r} is a whole number in 1..240", path="fps")
        if fps not in self._frames:
            count = math.floor((self.end_s - self.start_s) * fps + 1e-9) + 1
            if count > MAX_FRAMES:
                raise FloorError(f"{count} frames exceed {MAX_FRAMES}", path="fps")
            self._frames[fps] = tuple(self.sample(self.start_s + n / fps) for n in range(count))
        return self._frames[fps]

    def dance_frames(self, fps: int) -> tuple[DanceFrame, ...]:
        """:meth:`frames` as ordinary dance frames: each solved pose (feet held, the weight over them, the legs
        folded under the hips) as the deltas from this dancer's base, at the floor's centre. ``dance_pose(profile,
        frame, base=base)`` gives the same body without the spot, so anything that reads frames (a style check, a
        layer of lag and overshoot) reads the floor pass. The travel and turn are the frame's ``floor``; every rise
        and shift of the hips is its root."""
        spot, base = self.spot.frame(), self.base
        height, radius = self.profile.pelvis_height, self.profile.head_radius
        start = base.as_dict()
        out = []
        for solved in self.frames(fps):  # bounded by frames()
            root = solved.pose.root
            facing = base.root.rotation.inverse() * (spot.rotation.inverse() * root.rotation)
            local = base.root.rotation.inverse().rotate(spot.inverse_point(root.origin) - base.root.origin)
            values = solved.pose.as_dict()
            delta = {key: values.get(key, 0.0) - start.get(key, 0.0) for key in values.keys() | start.keys()}
            right, up, forward = (delta.pop(key, 0.0) for key in ("hips.right", "hips.up", "hips.forward"))
            joints = {key: value for key, value in delta.items() if abs(value) > 1e-12}
            out.append(
                replace(
                    self.frame(solved.time),
                    time=solved.time,
                    root=(right / radius, (up - local.y) / radius, forward / radius),
                    joints=MappingProxyType(joints),
                    planted=solved.planted,
                    floor=Floor(local.x / height, local.z / height, 0.0, heading(facing)),
                )
            )
        return tuple(out)

    def slip(self, fps: int) -> Slip:
        """How far planted feet slid, over the frames at ``fps`` and each plant's first and last moment: the ball
        from the spot it landed on, and the ankle from where it stood while the body did not turn."""
        run = self._pass
        ball_m = ankle_m = 0.0
        solved = {f.time: f.pose for f in self.frames(fps)}
        for side, holds in run.holds.items():
            offset = toes_offset(self.profile, side)
            for hold in holds:
                times = [hold.start, *(t for t in solved if hold.start < t < hold.end), hold.end]
                first: Vec3 | None = None
                for t in times:  # bounded by the frames at fps
                    frame = self.frame(t)
                    pose = solved[t] if t in solved else run.at(t, frame).pose
                    world = sk.world(self.profile, pose)
                    ankle, turned = run._ankle(hold, frame)
                    spot = ankle + yaw(turned).rotate(offset)
                    ball_m = max(ball_m, ball_of(self.profile, world, side).distance(spot))
                    if abs(frame.floor.turn - hold.turn) < 1e-9:
                        here = world[f"{side}_foot"].origin
                        first = first or here
                        ankle_m = max(ankle_m, here.distance(first))
        return Slip(ball_m, ankle_m)

    def balance(self, fps: int) -> tuple[BalanceFinding, ...]:
        """Every frame at ``fps`` on the floor whose centre of mass is not ``margin_m`` inside its support."""
        return tuple(
            BalanceFinding(f.time, f.margin_m, f.planted)
            for f in self.frames(fps)
            if f.margin_m is not None and f.margin_m < self.margin_m
        )

    def check(self, fps: int) -> None:
        """Refuse the dance with a :class:`BalanceError` if any frame at ``fps`` is off balance."""
        found = self.balance(fps)
        if found:
            raise BalanceError(found[:MAX_FINDINGS], len(found), self.profile.name)


def _source(source: object) -> Phrase | Routine:
    if not isinstance(source, (Phrase, Routine)):
        raise FloorError(
            f"a Phrase or a Routine is danced on the floor, not {type(source).__name__}; put a move in a Routine",
            path="source",
        )
    return source


def perform(
    source: Phrase | Routine,
    profile: sk.SkeletonProfile,
    groove: Groove,
    *,
    spot: Spot = CENTRE,
    base: sk.SkeletonPose | None = None,
    delay_beats: float = 0.0,
    clamp: bool = False,
    balance: bool = True,
    strict: bool = False,
    fps: int = 50,
    margin_m: float | None = None,
) -> Performance:
    """``source`` danced by ``profile`` from ``spot``, ``delay_beats`` after the groove's first beat. With ``strict``
    the frames at ``fps`` are checked for balance here, and the dance refused with a :class:`BalanceError`."""
    if not isinstance(groove, Groove):
        raise FloorError(f"a dance is performed on a music.Groove, not {type(groove).__name__}", path="groove")
    if not (checks.number(delay_beats) and 0 <= delay_beats <= 64):
        raise FloorError(f"delay_beats {delay_beats!r} lies in 0..64", path="delay_beats")
    run = Performance(
        _source(source),
        _check_profile(profile),
        groove,
        spot=spot,
        base=base,
        delay_s=delay_beats * groove.beat,
        size=1.0,
        clamp=_check_flag(clamp, "clamp"),
        balance=_check_flag(balance, "balance"),
        margin_m=margin_m,
    )
    if _check_flag(strict, "strict"):
        run.check(fps)
    return run


# --- several dancers ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Dancer:
    """One dancer of an ensemble: a character, where it stands, and how many beats it comes in late (a canon)."""

    profile: sk.SkeletonProfile
    spot: Spot = CENTRE
    delay_beats: float = 0.0
    base: sk.SkeletonPose | None = None


def formation(kind: str, count: int, spacing_m: float) -> tuple[Spot, ...]:
    """``count`` places ``spacing_m`` apart, all facing forward: a ``line`` across the floor, or a ``wedge`` with the
    first dancer in front and the others behind, alternately to the right and the left."""
    if kind not in FORMATIONS:
        raise FloorError(f"formation {kind!r} is one of {FORMATIONS}", path="kind")
    if type(count) is not int or not 1 <= count <= MAX_DANCERS:
        raise FloorError(f"count {count!r} is a whole number in 1..{MAX_DANCERS}", path="count")
    if not (checks.number(spacing_m) and 0.1 <= spacing_m <= 10):
        raise FloorError(f"spacing_m {spacing_m!r} lies in 0.1..10", path="spacing_m")
    if kind == "line":
        return tuple(Spot((i - (count - 1) / 2) * spacing_m, 0.0) for i in range(count))
    spots = [Spot(0.0, spacing_m / 2)]
    for i in range(1, count):
        row = (i + 1) // 2
        side = 1 if i % 2 else -1
        spots.append(Spot(side * row * spacing_m, spacing_m / 2 - row * spacing_m))
    return tuple(spots)


def ensemble(
    source: Phrase | Routine,
    dancers: Sequence[Dancer],
    groove: Groove,
    *,
    seed: int,
    variation: float = 1.0,
    clamp: bool = False,
    balance: bool = True,
    margin_m: float | None = None,
) -> tuple[Performance, ...]:
    """Each dancer's performance of one dance. A ``random.Random(seed)`` draws, dancer by dancer in order, a timing
    shift of up to ``MAX_JITTER_BEATS`` and a size of the moves within ``MAX_SIZE_VARIATION``, both times
    ``variation`` (0 for dancers in exact unison): the same seed gives the same ensemble."""
    if not (isinstance(dancers, (tuple, list)) and 1 <= len(dancers) <= MAX_DANCERS):
        raise FloorError(f"an ensemble holds 1..{MAX_DANCERS} dancers", path="dancers")
    if not all(isinstance(d, Dancer) for d in dancers):
        raise FloorError("every dancer is a dance_floor.Dancer", path="dancers")
    if type(seed) is not int or seed < 0:
        raise FloorError(f"seed {seed!r} is a whole number from 0", path="seed")
    if not (checks.number(variation) and 0 <= variation <= 1):
        raise FloorError(f"variation {variation!r} lies in 0..1", path="variation")
    if not isinstance(groove, Groove):
        raise FloorError(f"a dance is performed on a music.Groove, not {type(groove).__name__}", path="groove")
    rng = random.Random(seed)
    out = []
    for d in dancers:
        jitter = rng.uniform(-1.0, 1.0) * MAX_JITTER_BEATS * variation
        size = 1.0 + rng.uniform(-1.0, 1.0) * MAX_SIZE_VARIATION * variation
        if not (checks.number(d.delay_beats) and 0 <= d.delay_beats <= 64):
            raise FloorError(f"delay_beats {d.delay_beats!r} lies in 0..64", path="delay_beats")
        out.append(
            Performance(
                _source(source),
                _check_profile(d.profile),
                groove,
                spot=d.spot,
                base=d.base,
                delay_s=(d.delay_beats + jitter) * groove.beat,
                size=size,
                clamp=_check_flag(clamp, "clamp"),
                balance=_check_flag(balance, "balance"),
                margin_m=margin_m,
            )
        )
    return tuple(out)
