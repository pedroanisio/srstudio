"""Recorded mannequin motion on any character's skeleton, and on any song's beat (ADR 0188).

``motion_bridge`` gives srlocations' mannequin motion as turns of the canonical joints; this module reads those turns
into a ``skeleton.SkeletonProfile``'s controls, holds the feet the clip plants still on a character of other
proportions, and moves the clip's beats onto a song's:

    clip = motion_bridge.load("walk-2m-30fps.json")
    toon = skeleton.preset("cartoon")
    walk = retarget.retarget(clip, toon)              # a pose per frame, planted feet held, a report of what changed
    one = retarget.to_pose(clip, toon, time=0.51)     # any moment, slerped between frames
    beat = retarget.beat_map(clip, music.Groove(120), music.Groove(129))
    dance = retarget.perform(clip, toon, beat)
    dance.pose(beat.start_s + 1.0)                    # the pose at a second of the song

A performance plays each control and the hips' place between frames through a cubic spline with its velocity and
acceleration continuous, and its beat map eases its rate between beats, so a gesture keeps its timing and acceleration
on the song's clock (ADR 0204); ``to_pose`` at a time, a single moment, slerps between the frames either side.

Values are absolute turns from the T-stance, the skeleton's zero, so a profile's ``rest`` is not added. A control the
clip turns past the profile's limits is refused with every such value listed, unless ``clamp=True`` holds it at the
limit and the report counts it. A joint the profile omits is dropped and reported; no kept joint is moved by that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import motion_bridge as mb
from . import skeleton as sk
from ._retarget_errors import AnchorOrderError as AnchorOrderError
from ._retarget_errors import BeatWarpError as BeatWarpError
from ._retarget_errors import EmptyOverlapError as EmptyOverlapError
from ._retarget_errors import LimitBreach as LimitBreach
from ._retarget_errors import RetargetError as RetargetError
from ._retarget_errors import RetargetInputError as RetargetInputError
from ._retarget_errors import RetargetLimitError as RetargetLimitError
from ._retarget_errors import WarpRateError as WarpRateError
from ._retarget_feet import BLEND_S as BLEND_S
from ._retarget_feet import PLANT_HEIGHT_M as PLANT_HEIGHT_M
from ._retarget_feet import PLANT_SPEED_M_S as PLANT_SPEED_M_S
from ._retarget_feet import FootLock as FootLock
from ._retarget_feet import LockPlan, check_plants, lock
from ._retarget_feet import Plant as Plant
from ._retarget_feet import foot_slip as foot_slip
from ._retarget_feet import plants as plants
from ._retarget_play import Tracks
from ._retarget_pose import MAX_LISTED as MAX_LISTED
from ._retarget_pose import RESIDUAL_FLOOR as RESIDUAL_FLOOR
from ._retarget_pose import Clamp as Clamp
from ._retarget_pose import Dropped as Dropped
from ._retarget_pose import Residual as Residual
from ._retarget_pose import RetargetReport as RetargetReport
from ._retarget_pose import (
    Tally,
    Turns,
    check_clip,
    check_profile,
    frame_turns,
    locate,
    posed,
    root_frame,
    root_scale,
    solve,
    turns_at,
)
from ._retarget_warp import MAX_ANCHORS as MAX_ANCHORS
from ._retarget_warp import MAX_PER as MAX_PER
from ._retarget_warp import MAX_RATE as MAX_RATE
from ._retarget_warp import MIN_PER as MIN_PER
from ._retarget_warp import MIN_RATE as MIN_RATE
from ._retarget_warp import BeatMap as BeatMap
from ._retarget_warp import beat_map as beat_map

MAX_FPS = 120.0  # pictures a second a performance is sampled at
MAX_FRAMES = 14_400  # samples one call makes: eight minutes at 30 fps

__all__ = [
    "BLEND_S",
    "MAX_ANCHORS",
    "MAX_FPS",
    "MAX_FRAMES",
    "MAX_LISTED",
    "MAX_PER",
    "MAX_RATE",
    "MIN_PER",
    "MIN_RATE",
    "PLANT_HEIGHT_M",
    "PLANT_SPEED_M_S",
    "RESIDUAL_FLOOR",
    "AnchorOrderError",
    "BeatMap",
    "BeatWarpError",
    "Clamp",
    "Dropped",
    "EmptyOverlapError",
    "FootLock",
    "LimitBreach",
    "Performance",
    "Plant",
    "Residual",
    "RetargetError",
    "RetargetInputError",
    "RetargetLimitError",
    "RetargetReport",
    "Retargeted",
    "RetargetedPose",
    "SongFrames",
    "WarpRateError",
    "beat_map",
    "foot_slip",
    "perform",
    "plants",
    "retarget",
    "root_scale",
    "to_pose",
]


@dataclass(frozen=True)
class RetargetedPose:
    """One pose of the character and what retargeting it changed."""

    pose: sk.SkeletonPose
    report: RetargetReport


@dataclass(frozen=True)
class Retargeted:
    """A clip on one character: a pose per clip frame at ``times_s`` on the clip's clock, the plants found in the clip,
    the holds that kept those feet still (``locks``, empty when locking was off) and the report."""

    profile: sk.SkeletonProfile
    times_s: tuple[float, ...]
    poses: tuple[sk.SkeletonPose, ...]
    report: RetargetReport
    plants: tuple[Plant, ...]
    locks: tuple[FootLock, ...]


@dataclass(frozen=True)
class SongFrames:
    """A performance sampled at a picture rate: song seconds, a pose at each, and the report over all of them."""

    times_s: tuple[float, ...]
    poses: tuple[sk.SkeletonPose, ...]
    report: RetargetReport


def _flag(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise RetargetInputError("True or False", path=path, actual=value, expected=[True, False])
    return value


def to_pose(
    clip: mb.MotionClip,
    profile: sk.SkeletonProfile,
    *,
    index: int | None = None,
    time: float | None = None,
    clamp: bool = False,
) -> RetargetedPose:
    """The character's pose at one frame (``index``) or one second on the clip's clock (``time``), each joint on the
    branch nearest the T-stance. A time between frames slerps each turn and lerps the hips. Feet are not held: a
    single moment has no plant to hold."""
    clip, profile = check_clip(clip), check_profile(profile)
    tally = Tally(_flag(clamp, "clamp"))
    if index is not None and time is None:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < clip.frame_count:
            raise RetargetInputError(
                "a frame of the clip", path="index", actual=index, expected=[0, clip.frame_count - 1]
            )
        turns = frame_turns(clip.frames[index])
    elif time is not None and index is None:
        turns = turns_at(clip, time)
    else:
        raise RetargetInputError("give exactly one of index and time", path="index", actual=[index, time])
    scale = root_scale(clip, profile)
    values = solve(profile, turns, scale, tally)
    tally.refuse()
    return RetargetedPose(posed(profile, values, root_frame(turns, scale)), tally.report(profile, scale))


def _free(
    clip: mb.MotionClip, profile: sk.SkeletonProfile, scale: float, tally: Tally
) -> tuple[list[dict[str, float]], list[sk.SkeletonPose]]:
    """Every frame read in order, each joint's branch nearest the frame before, so a turn past half a turn stays
    continuous."""
    values: list[dict[str, float]] = []
    poses: list[sk.SkeletonPose] = []
    for frame in clip.frames:
        turns = frame_turns(frame)
        values.append(solve(profile, turns, scale, tally, values[-1] if values else None))
        poses.append(posed(profile, values[-1], root_frame(turns, scale)))
    return values, poses


def retarget(
    clip: mb.MotionClip,
    profile: sk.SkeletonProfile,
    *,
    clamp: bool = False,
    lock_feet: bool = True,
    planted: tuple[Plant, ...] | None = None,
) -> Retargeted:
    """Every frame of ``clip`` on ``profile``. With ``lock_feet`` each foot the clip plants (``planted``, or what
    :func:`plants` finds) is held still while planted, on every side the profile has a whole leg."""
    clip, profile = check_clip(clip), check_profile(profile)
    tally = Tally(_flag(clamp, "clamp"))
    locking = _flag(lock_feet, "lock_feet")
    scale = root_scale(clip, profile)
    values, poses = _free(clip, profile, scale, tally)
    found = plants(clip) if planted is None else check_plants(planted, clip)
    times = tuple(frame.time_s for frame in clip.frames)
    locks: tuple[FootLock, ...] = ()
    if locking:
        plan = LockPlan.build(profile, poses, found)
        worst = {plant: 0.0 for plant, _ in plan.holds}
        for i, frame in enumerate(clip.frames):
            root = poses[i].root
            held, misses = lock(profile, plan, values[i], root, frame.time_s, tally)
            poses[i] = posed(profile, held, root)
            for plant in worst:
                if plant.side in misses and plant.first <= i <= plant.last:
                    worst[plant] = max(worst[plant], misses[plant.side])
        locks = tuple(
            FootLock(plant.side, plant.start_s, plant.end_s, target, worst[plant]) for plant, target in plan.holds
        )
    tally.refuse()
    return Retargeted(profile, times, tuple(poses), tally.report(profile, scale), found, locks)


class Performance:
    """A clip on one character, played on a song's clock through a :class:`BeatMap`. Built by :func:`perform`."""

    def __init__(
        self,
        clip: mb.MotionClip,
        profile: sk.SkeletonProfile,
        beats: BeatMap,
        *,
        clamp: bool,
        lock_feet: bool,
        planted: tuple[Plant, ...] | None,
    ) -> None:
        self.clip, self.profile, self.beats = clip, profile, beats
        self.clamp, self.lock_feet = clamp, lock_feet
        self._scale = root_scale(clip, profile)
        tally = Tally(clamp)
        _, free = _free(clip, profile, self._scale, tally)
        tally.refuse()
        self._tracks = Tracks.read(clip, profile, self._scale)
        self.plants = plants(clip) if planted is None else check_plants(planted, clip)
        self._plan = LockPlan.build(profile, free, self.plants) if lock_feet else LockPlan(())

    @property
    def start_s(self) -> float:
        return self.beats.start_s

    @property
    def end_s(self) -> float:
        return self.beats.end_s

    def _pose(self, song_s: float, tally: Tally) -> sk.SkeletonPose:
        moment = self.beats.clip_time(song_s)
        index, share = locate(self.clip, moment)
        values = self._tracks.controls(self.profile, index, share, moment, tally)
        root = root_frame(Turns(moment, self._tracks.place(index, share), {}), self._scale)
        if self.lock_feet:
            values, _ = lock(self.profile, self._plan, values, root, moment, tally)
        return posed(self.profile, values, root)

    def sample(self, song_s: float) -> RetargetedPose:
        """The pose at the song's second ``song_s``, with the report of that one sample."""
        tally = Tally(self.clamp)
        found = self._pose(song_s, tally)
        tally.refuse()
        return RetargetedPose(found, tally.report(self.profile, self._scale))

    def pose(self, song_s: float) -> sk.SkeletonPose:
        """The pose at the song's second ``song_s``."""
        return self.sample(song_s).pose

    def frames(self, fps: float) -> SongFrames:
        """The performance at ``fps`` pictures a second from its start, at most ``MAX_FRAMES`` of them."""
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not 0 < fps <= MAX_FPS:
            raise RetargetInputError("pictures a second", path="fps", actual=fps, expected=[0, MAX_FPS])
        count = math.floor(self.beats.duration_s * fps + 1e-9) + 1
        if count > MAX_FRAMES:
            raise RetargetInputError(
                "too many pictures for one call", path="fps", actual=count, expected=f"at most {MAX_FRAMES}"
            )
        tally = Tally(self.clamp)
        times = tuple(self.start_s + i / fps for i in range(count))
        poses = tuple(self._pose(t, tally) for t in times)
        tally.refuse()
        return SongFrames(times, poses, tally.report(self.profile, self._scale))


def perform(
    clip: mb.MotionClip,
    profile: sk.SkeletonProfile,
    beats: BeatMap,
    *,
    clamp: bool = False,
    lock_feet: bool = True,
    planted: tuple[Plant, ...] | None = None,
) -> Performance:
    """``clip`` on ``profile`` on the song clock of ``beats``: every frame is read once here, and refused here if a
    control passes its limits without ``clamp``; each later sample plays every control between the frames either side on
    its spline (ADR 0204)."""
    clip, profile = check_clip(clip), check_profile(profile)
    if not isinstance(beats, BeatMap):
        raise RetargetInputError("expected a BeatMap from beat_map", path="beats", actual=type(beats).__name__)
    return Performance(
        clip, profile, beats, clamp=_flag(clamp, "clamp"), lock_feet=_flag(lock_feet, "lock_feet"), planted=planted
    )
