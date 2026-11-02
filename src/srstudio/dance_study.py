"""How a body dances, measured the same way on a real dancer and on ours, so the two can be compared (ADR 0200).

A reference video is read by a pose estimator (``tools/pose_extract.py``) into a ``srstudio.pose-track/1.0.0``
record; :func:`reference_body` turns the record into a :class:`BodyTrack`. One of our dances, any sequence of
:class:`dance.DanceFrame` (a move, a routine, a phrase) sampled on a preset skeleton, becomes one with
:func:`dance_body`. :func:`measure_style` measures either on a song's beat grid with the same code, and
:mod:`srstudio.dance_style` turns a reference's measures into targets and lists what one of ours misses.

A body track holds thirteen points, each a place both a pose estimator and the canonical skeleton have: the hip,
knee, ankle, shoulder, elbow and wrist joints of each side and the centre of the head. They are in head radii of a
body of realistic proportions, scaled by the torso (shoulders' middle to hips' middle), from the hips' middle, in the
skeleton's axes: x the dancer's right, y down, z the dancer's front. Scaling by the torso and starting at the hips
removes the camera's distance and its travel; a camera's tilt and roll remain, and the channels they reach say so.

The estimator is a model, so its frames are untrusted. A frame is refused, and counted under its reason, when the
dancer was lost, when a hip or a shoulder is seen with too little confidence, when a bone of the legs or the torso is
far from its own length in the rest of the clip, and when a point jumps further in one frame than a body can move. An
arm whose bone is far from its length is left out of that frame, which is counted under ``arm``, and a point seen with
too little confidence is left out of the channels that use it in that frame. Nothing is filled in: each channel is
measured on the runs of frames where it is seen.

Each channel is read in windows of :data:`WINDOW_BEATS` beats, every :data:`HOP_BEATS`: the groove of the window by
:func:`dance.measure_dance` (its size, cycles per beat, snap and hit against the beat), and the window's range. A
window is read when it sees :data:`MIN_COVERAGE` of its frames and no gap is longer than :data:`MAX_GAP_BEATS`; the
missing frames stay missing, and the groove is fitted on the frames seen. A window whose strongest motion is not a
cycle reads as unreadable, never as a poor groove. The spread of the windows (10th to 90th percentile) and the
channel's noise are the uncertainty a reading carries.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from types import MappingProxyType

import numpy as np

from . import checks
from . import pose_track as pt
from . import skeleton as sk
from ._dance_measure import DanceMeasureError, DanceReading, measure_dance
from ._dance_model import DanceError
from ._dance_sample import DanceFrame
from .dance_pose import dance_pose
from .music import Groove

__all__ = [
    "CHANNELS",
    "HOP_BEATS",
    "LAGS",
    "POINTS",
    "WINDOW_BEATS",
    "BodyTrack",
    "Channel",
    "ChannelReading",
    "DanceStudyError",
    "LagReading",
    "Spread",
    "StyleReading",
    "dance_body",
    "measure_style",
    "pose_record",
    "reference_body",
]

POINTS = (
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "head",
)
_AT = {name: i for i, name in enumerate(POINTS)}
LANDMARKS_OF = {name: (name,) for name in POINTS[:-1]} | {"head": ("left_ear", "right_ear")}
JOINT_OF = {  # the canonical joint whose origin is each point; the head's centre is half way to its crown
    "left_hip": "left_upper_leg",
    "right_hip": "right_upper_leg",
    "left_knee": "left_lower_leg",
    "right_knee": "right_lower_leg",
    "left_ankle": "left_foot",
    "right_ankle": "right_foot",
    "left_shoulder": "left_upper_arm",
    "right_shoulder": "right_upper_arm",
    "left_elbow": "left_lower_arm",
    "right_elbow": "right_lower_arm",
    "left_wrist": "left_hand",
    "right_wrist": "right_hand",
}
BONES = (  # pairs whose length a body keeps, checked frame by frame on a reference
    ("left_hip", "right_hip"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "left_knee"),
    ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"),
    ("right_knee", "right_ankle"),
    ("left_shoulder", "left_elbow"),
    ("right_shoulder", "right_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_elbow", "right_wrist"),
)
CORE = ("left_hip", "right_hip", "left_shoulder", "right_shoulder")
ARM_POINTS = ("left_elbow", "right_elbow", "left_wrist", "right_wrist")  # an arm misread leaves the body standing
MIN_VISIBILITY = 0.5
BONE_RATIO = 1.5  # a bone this many times longer or shorter than its own median is a misread
MAX_STEP = 3.0  # head radii a point may move in a 30th of a second; a hand at 10 m/s moves about one
WINDOW_BEATS = 8  # an eight-count, the phrase a hip-hop class counts in
HOP_BEATS = 2
MIN_WINDOWS = 4  # fewer windows than this give no spread worth a target
MIN_COVERAGE = 0.6  # of a window's frames seen, or it is not read
MAX_GAP_BEATS = 1.0  # a window with a longer gap loses the cycle's phase: it is not read
LOCKS = (0.5, 1.0, 2.0)  # cycles per beat a groove locks to
LOCK_TOLERANCE = 0.08
MIN_CORRELATION = 0.3
STILL = 1e-6  # a window that moves less than this, in its channel's unit, does not move
REFERENCE_PRESET = "realistic"


class DanceStudyError(DanceError):
    """A track, a dance or a grid that cannot be measured as given."""


def _bad(condition: bool, message: str, path: str) -> None:
    if condition:
        raise DanceStudyError(message, code="dance.study", path=path)


@cache
def torso_head_radii() -> float:
    """The torso (shoulders' middle to hips' middle) of a realistic body at rest, in its head radii: every track is
    scaled so that its torso measures this."""
    profile = sk.preset(REFERENCE_PRESET)
    joints = sk.world(profile, sk.rest_pose(profile))
    return _torso_m(joints) / profile.proportions.head_radius_m


def _torso_m(joints: Mapping[str, sk.Frame]) -> float:
    def mid(a: str, b: str) -> np.ndarray:
        return (_xyz(joints[a].origin) + _xyz(joints[b].origin)) / 2

    return float(np.linalg.norm(mid("left_upper_arm", "right_upper_arm") - mid("left_upper_leg", "right_upper_leg")))


def _xyz(v: sk.Vec3) -> np.ndarray:
    return np.array([v.x, v.y, v.z], float)


@dataclass(frozen=True, eq=False)
class BodyTrack:
    """``points`` (frames x 13 x 3) in head radii from the hips' middle, skeleton axes; ``seen`` (frames x 13) which
    are usable; ``start`` the first frame's second; ``rejected`` how many frames were refused, by reason."""

    fps: int
    start: float
    points: np.ndarray
    seen: np.ndarray
    rejected: Mapping[str, int]
    source: str

    def __post_init__(self) -> None:
        _bad(type(self.fps) is not int or not 1 <= self.fps <= 240, f"fps {self.fps!r} is a whole number", "fps")
        _bad(not checks.number(self.start) or self.start < 0, f"start {self.start!r} is a second from 0", "start")
        n = len(self.points)
        _bad(self.points.shape != (n, len(POINTS), 3) or n < 1, "points are frames x 13 x 3", "points")
        _bad(self.seen.shape != (n, len(POINTS)) or self.seen.dtype != bool, "seen is frames x 13 of bool", "seen")
        _bad(not np.isfinite(self.points[self.seen]).all(), "a seen point is a finite place", "points")

    @property
    def frames(self) -> int:
        return len(self.points)

    @property
    def used(self) -> int:
        """Frames with the hips and shoulders seen."""
        return int(self.seen[:, [_AT[p] for p in CORE]].all(axis=1).sum())


# --- a reference, from a pose estimator's record -------------------------------------------------------------------


def reference_body(track: pt.PoseTrack, *, min_visibility: float = MIN_VISIBILITY) -> BodyTrack:
    """The dancer in ``track`` as a body track, with each refused frame counted under its reason."""
    _bad(not isinstance(track, pt.PoseTrack), "a reference is a pose_track.PoseTrack", "track")
    _bad(not (checks.number(min_visibility) and 0 < min_visibility < 1), "min_visibility lies in 0..1", "visibility")
    fps = round(track.fps)
    _bad(abs(track.fps - fps) > 1e-3, f"a track at {track.fps} fps: resample the video to whole frames", "fps")
    n = len(track.frames)
    points = np.full((n, len(POINTS), 3), np.nan)
    seen = np.zeros((n, len(POINTS)), bool)
    rejected = {"lost": 0, "low_confidence": 0, "implausible": 0, "jump": 0, "arm": 0}
    index = {name: i for i, name in enumerate(pt.LANDMARKS)}
    for f, frame in enumerate(track.frames):
        if frame.world is None or frame.image is None:
            rejected["lost"] += 1
            continue
        world = np.asarray(frame.world, float) * (-1.0, 1.0, -1.0)  # estimator's axes to the skeleton's
        visibility = np.asarray([row[3] for row in frame.image], float)
        for p, name in enumerate(POINTS):
            marks = [index[m] for m in LANDMARKS_OF[name]]
            points[f, p] = world[marks].mean(axis=0)
            seen[f, p] = bool(visibility[marks].min() >= min_visibility)
        if not seen[f, [_AT[c] for c in CORE]].all():
            rejected["low_confidence"] += 1
            seen[f] = False
    _bad(not seen.any(), "no frame of the track holds the dancer's hips and shoulders: nothing to measure", "track")
    torso = _torso(points)
    scale = torso_head_radii() / float(np.median(torso[seen[:, _AT["left_hip"]]]))
    points *= scale
    medians = {bone: _median_length(points, seen, bone) for bone in BONES}
    last = None
    for f in range(n):
        if not seen[f].any():
            last = None
            continue
        broken = _broken(points[f], seen[f], medians)
        if broken - set(ARM_POINTS):
            rejected["implausible"] += 1
            seen[f] = False
            continue
        if broken:
            rejected["arm"] += 1
            for side in {name.split("_")[0] for name in broken}:
                seen[f, [_AT[p] for p in ARM_POINTS if p.startswith(side)]] = False
        if last is not None and last == f - 1:
            both = seen[f] & seen[last]
            step = np.linalg.norm(points[f, both] - points[last, both], axis=1)
            if both.any() and float(step.max()) > MAX_STEP * 30 / fps:
                rejected["jump"] += 1
                seen[f] = False
                last = None
                continue
        last = f
    points[~seen] = np.nan
    return BodyTrack(fps, track.frames[0].time_s, points, seen, MappingProxyType(rejected), "reference")


def _mid(points: np.ndarray, a: str, b: str) -> np.ndarray:
    return (points[..., _AT[a], :] + points[..., _AT[b], :]) / 2


def _torso(points: np.ndarray) -> np.ndarray:
    return np.linalg.norm(
        _mid(points, "left_shoulder", "right_shoulder") - _mid(points, "left_hip", "right_hip"), axis=-1
    )


def _median_length(points: np.ndarray, seen: np.ndarray, bone: tuple[str, str]) -> float | None:
    a, b = _AT[bone[0]], _AT[bone[1]]
    both = seen[:, a] & seen[:, b]
    if not both.any():
        return None
    return float(np.median(np.linalg.norm(points[both, a] - points[both, b], axis=1)))


def _broken(frame: np.ndarray, seen: np.ndarray, medians: Mapping[tuple[str, str], float | None]) -> set[str]:
    """The sides whose arm, and the bones of the body whose length, is far from its own median in this frame, by the
    names of their points; an arm's bone names its elbow, a leg's or the torso's names its points."""
    out: set[str] = set()
    for (a, b), median in medians.items():
        i, j = _AT[a], _AT[b]
        if median and seen[i] and seen[j]:
            ratio = float(np.linalg.norm(frame[i] - frame[j])) / median
            if not 1 / BONE_RATIO <= ratio <= BONE_RATIO:
                out |= {p for p in (a, b) if p in ARM_POINTS} or {a, b}
    return out


# --- ours, from dance frames on a preset skeleton ------------------------------------------------------------------


def _skeleton_points(profile: sk.SkeletonProfile, pose: sk.SkeletonPose) -> np.ndarray:
    joints = sk.world(profile, pose)
    out = np.empty((len(POINTS), 3))
    for name, joint in JOINT_OF.items():
        out[_AT[name]] = _xyz(joints[joint].origin)
    head = joints["head"]
    tip = profile.tip("head")
    crown = _xyz(head.point(tip)) if tip is not None else _xyz(head.origin) - (0, 2 * profile.head_radius, 0)
    out[_AT["head"]] = (_xyz(head.origin) + crown) / 2
    return out


def dance_body(
    frames: Sequence[DanceFrame],
    fps: int,
    *,
    profile: sk.SkeletonProfile | None = None,
    base: sk.SkeletonPose | None = None,
    clamp: bool = True,
) -> BodyTrack:
    """``frames``, sampled ``fps`` times a second, danced on ``profile`` (realistic by default) through
    :func:`dance_pose`, as a body track. The skeleton holds no foot on the floor: a bob on the root moves the whole
    body, feet and all, which is what this measures."""
    _bad(type(fps) is not int or not 1 <= fps <= 240, f"fps {fps!r} is a whole number in 1..240", "fps")
    frames = list(frames)
    _bad(not frames or not all(isinstance(f, DanceFrame) for f in frames), "frames are dance.DanceFrame", "frames")
    start = frames[0].time
    off = max(abs(f.time - (start + i / fps)) for i, f in enumerate(frames))
    _bad(off > 1e-6, f"frames are {1 / fps:.4f} s apart from the first; one is {off:.4f} s off", "frames")
    profile = profile if profile is not None else sk.preset(REFERENCE_PRESET)
    rest = _skeleton_points(profile, base if base is not None else sk.rest_pose(profile))
    scale = torso_head_radii() / float(_torso(rest))
    points = np.empty((len(frames), len(POINTS), 3))
    for i, frame in enumerate(frames):
        here = _skeleton_points(profile, dance_pose(profile, frame, base=base, clamp=clamp).pose)
        points[i] = (here - _mid(here, "left_hip", "right_hip")) * scale
    seen = np.ones(points.shape[:2], bool)
    return BodyTrack(fps, start, points, seen, MappingProxyType({}), "dance")


# --- channels ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Channel:
    """A measure of the body in every frame: its ``unit``, how far a monocular estimate with a moving camera can be
    trusted on it (``good``, ``fair`` or ``poor``) and why, the points it reads, and whether it is read as a groove."""

    name: str
    unit: str
    trust: str
    why: str
    points: tuple[str, ...]
    groove: bool = True


_LEGS = ("left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")
_ARMS = ("left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist")
CHANNELS: tuple[Channel, ...] = (
    Channel(
        "hips.bounce",
        "head_radii",
        "fair",
        "the hips' height over the lower ankle: depth errors on the feet and the camera's tilt shorten it",
        ("left_hip", "right_hip", "left_ankle", "right_ankle"),
    ),
    Channel("knees.bend", "rad", "fair", "a 3D angle at the knee: depth on a bent leg is the estimator's guess", _LEGS),
    Channel("torso.lean", "rad", "poor", "front-back lean against the camera's vertical, which tilts with it", CORE),
    Channel("torso.roll", "rad", "poor", "side lean against the camera's vertical, which rolls with it", CORE),
    Channel("torso.twist", "rad", "fair", "shoulders turned on the hips: needs depth, but no camera angle", CORE),
    Channel("shoulders.tilt", "rad", "good", "shoulder line against the hip line, both in the picture's plane", CORE),
    Channel(
        "head.bob",
        "head_radii",
        "good",
        "the head's height over the shoulders' middle",
        ("left_shoulder", "right_shoulder", "head"),
    ),
    Channel(
        "head.sway",
        "head_radii",
        "good",
        "the head along the shoulder line",
        ("left_shoulder", "right_shoulder", "head"),
    ),
    Channel(
        "arms.height",
        "head_radii",
        "good",
        "the wrists' height over the shoulders' middle; a hidden wrist leaves its frame out",
        ("left_shoulder", "right_shoulder", "left_wrist", "right_wrist"),
    ),
    Channel("arms.reach", "ratio", "fair", "shoulder to wrist over the arm's length: depth on a pointing arm", _ARMS),
    Channel(
        "hands.travel",
        "head_radii_per_beat",
        "fair",
        "the wrists' path around the hips each beat, a quarter beat at a time; noise lengthens it",
        ("left_hip", "right_hip", "left_wrist", "right_wrist"),
        groove=False,
    ),
    Channel(
        "feet.travel",
        "head_radii_per_beat",
        "fair",
        "the ankles' path around the hips each beat, a quarter beat at a time: steps and kicks",
        ("left_hip", "right_hip", "left_ankle", "right_ankle"),
        groove=False,
    ),
    Channel(
        "stance.width",
        "head_radii",
        "fair",
        "the ankles' distance across the floor",
        ("left_ankle", "right_ankle"),
        groove=False,
    ),
)
CHANNEL = {c.name: c for c in CHANNELS}
UNMEASURED = {
    "root.travel": "the hips' path on the floor: a camera that follows the dancer moves the picture with them, and "
    "the estimator's metres start at the hips, so no frame of reference stays on the floor"
}
LAG_POINTS = {
    "hips": ("left_hip", "right_hip"),
    "chest": ("left_shoulder", "right_shoulder"),
    "head": ("head",),
    "hands": ("left_wrist", "right_wrist"),
}
LAGS = (("hips", "chest"), ("chest", "head"), ("hips", "head"), ("chest", "hands"))


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(norm > 1e-12, norm, 1.0)


def _flat(v: np.ndarray) -> np.ndarray:
    return v * (1.0, 0.0, 1.0)


def _angle(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    cos = np.sum(_unit(a) * _unit(b), axis=-1)
    return np.arccos(np.clip(cos, -1.0, 1.0))


def _height(points: np.ndarray, name: str) -> np.ndarray:
    """A point's height over the lower ankle (y is down)."""
    low = np.maximum(points[:, _AT["left_ankle"], 1], points[:, _AT["right_ankle"], 1])
    return low - points[:, _AT[name], 1]


def _values(points: np.ndarray, name: str) -> np.ndarray:
    """A channel's value in every frame (NaN where its points are not seen)."""
    p = {k: points[:, i] for k, i in _AT.items()}
    hips, shoulders = _mid(points, "left_hip", "right_hip"), _mid(points, "left_shoulder", "right_shoulder")
    across = _unit(_flat(p["right_hip"] - p["left_hip"]))
    front = _unit(np.cross(across, (0.0, 1.0, 0.0)))
    trunk = shoulders - hips
    line = p["right_shoulder"] - p["left_shoulder"]
    if name == "hips.bounce":
        low = np.maximum(p["left_ankle"][:, 1], p["right_ankle"][:, 1])
        return low - hips[:, 1]
    if name == "knees.bend":
        return np.mean(
            [
                math.pi - _angle(p[f"{s}_hip"] - p[f"{s}_knee"], p[f"{s}_ankle"] - p[f"{s}_knee"])
                for s in ("left", "right")
            ],
            axis=0,
        )
    if name == "torso.lean":
        return np.arctan2(np.sum(trunk * front, axis=1), -trunk[:, 1])
    if name == "torso.roll":
        return np.arctan2(np.sum(trunk * across, axis=1), -trunk[:, 1])
    if name == "torso.twist":
        flat = _unit(_flat(line))
        return np.arctan2(np.cross(across, flat)[:, 1], np.sum(across * flat, axis=1))

    def tilt(v: np.ndarray) -> np.ndarray:
        return np.arctan2(-v[:, 1], np.linalg.norm(_flat(v), axis=1))

    if name == "shoulders.tilt":
        return tilt(line) - tilt(p["right_hip"] - p["left_hip"])
    if name == "head.bob":
        return shoulders[:, 1] - p["head"][:, 1]
    if name == "head.sway":
        return np.sum((p["head"] - shoulders) * _unit(line), axis=1)
    if name == "arms.height":
        return np.mean([shoulders[:, 1] - p[f"{s}_wrist"][:, 1] for s in ("left", "right")], axis=0)
    if name == "arms.reach":
        return np.mean(
            [
                np.linalg.norm(p[f"{s}_wrist"] - p[f"{s}_shoulder"], axis=1)
                / (
                    np.linalg.norm(p[f"{s}_elbow"] - p[f"{s}_shoulder"], axis=1)
                    + np.linalg.norm(p[f"{s}_wrist"] - p[f"{s}_elbow"], axis=1)
                )
                for s in ("left", "right")
            ],
            axis=0,
        )
    if name == "stance.width":
        return np.linalg.norm(_flat(p["left_ankle"] - p["right_ankle"]), axis=1)
    raise DanceStudyError(f"no channel {name!r}", path="channel")


def channel(track: BodyTrack, name: str) -> tuple[np.ndarray, np.ndarray]:
    """A groove or level channel's values and the frames where all its points are seen."""
    _bad(name not in CHANNEL, f"no channel {name!r}; there are {sorted(CHANNEL)}", "channel")
    valid = track.seen[:, [_AT[p] for p in CHANNEL[name].points]].all(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        values = (
            _values(track.points, name)
            if name not in ("hands.travel", "feet.travel")
            else np.full(track.frames, np.nan)
        )
    valid &= np.isfinite(values)
    return np.where(valid, values, np.nan), valid


def _runs(valid: np.ndarray) -> list[tuple[int, int]]:
    """The [start, end) runs of consecutive valid frames."""
    edges = np.diff(np.concatenate(([0], valid.astype(int), [0])))
    return list(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist(), strict=True))


# --- readings ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Spread:
    """Percentiles of a measure across windows or frames, and how many there were."""

    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    count: int

    @classmethod
    def of(cls, values: Sequence[float] | np.ndarray) -> Spread | None:
        x = np.asarray(values, float)
        x = x[np.isfinite(x)]
        if not len(x):
            return None
        p10, p25, p50, p75, p90 = (float(v) for v in np.percentile(x, (10, 25, 50, 75, 90)))
        return cls(p10, p25, p50, p75, p90, len(x))


@dataclass(frozen=True)
class ChannelReading:
    """A channel over a track: ``level`` its value across frames; ``noise`` the frame-to-frame jitter a smooth motion
    would not have (an upper bound on the estimate's own error, per frame); windows in all, ``read`` holding a groove,
    ``still`` not moving; across read and still windows the groove's ``peak_to_peak``, and across read windows its
    ``cycles_per_beat``, ``snap_ratio`` and, on windows ``locked`` to a half, one or two cycles a beat,
    ``hit_offset`` in beats; ``range`` the 5th to 95th percentile span of each window."""

    name: str
    unit: str
    trust: str
    frames: int
    level: Spread | None
    noise: float | None
    windows: int
    read: int
    still: int
    locked: int
    peak_to_peak: Spread | None
    range: Spread | None
    cycles_per_beat: Spread | None
    snap_ratio: Spread | None
    hit_offset: Spread | None


@dataclass(frozen=True)
class LagReading:
    """How late ``follow`` moves up and down after ``lead``, in beats, across windows where their motions correlate
    by at least :data:`MIN_CORRELATION`; ``correlation`` the windows' peak correlations."""

    lead: str
    follow: str
    windows: int
    read: int
    beats: Spread | None
    correlation: Spread | None


@dataclass(frozen=True)
class StyleReading:
    """A body track measured on a grid: every channel and lag, the frames used, and those refused by reason."""

    bpm: float
    offset: float
    fps: int
    frames: int
    used: int
    rejected: Mapping[str, int]
    channels: Mapping[str, ChannelReading]
    lags: Mapping[str, LagReading]


_SMOOTH = np.array([-3.0, 12.0, 17.0, 12.0, -3.0]) / 35  # a five-frame local quadratic fit (Savitzky-Golay)
_SMOOTH_GAIN = math.sqrt(630 / 1225)  # what the fit leaves of white noise, as a share of its deviation


def _noise(values: np.ndarray, runs: list[tuple[int, int]]) -> float | None:
    """The frame-to-frame jitter a motion smooth over five frames would not have: the median absolute residual from a
    local quadratic fit, as a standard deviation. A quadratic follows a dance's curves, so what it leaves is mostly the
    estimate's own scatter; motion faster than five frames still counts, so it is an upper bound."""
    left = [values[a:b][2:-2] - np.convolve(values[a:b], _SMOOTH, "valid") for a, b in runs if b - a >= 5]
    residual = np.concatenate(left or [np.empty(0)])
    if len(residual) < 8:
        return None
    return float(1.4826 * np.median(np.abs(residual - np.median(residual))) / _SMOOTH_GAIN)


def _windows(valid: np.ndarray, size: int, hop: int, gap: int) -> list[tuple[int, int]]:
    """The [start, end) windows of ``size`` frames, every ``hop``, that see at least ``MIN_COVERAGE`` of their frames
    and leave no gap longer than ``gap`` frames."""
    out = []
    for i in range(0, len(valid) - size + 1, hop):
        here = valid[i : i + size]
        if here.mean() >= MIN_COVERAGE and max((b - a for a, b in _runs(~here)), default=0) <= gap:
            out.append((i, i + size))
    return out


def _groove(values: np.ndarray, windows: list[tuple[int, int]], track: BodyTrack, groove: Groove):
    readings: list[DanceReading] = []
    ptp, spans, still = [], [], 0
    for a, b in windows:
        x = values[a:b]
        lo, hi = np.nanpercentile(x, (5, 95))
        spans.append(float(hi - lo))
        if float(np.nanmax(x) - np.nanmin(x)) < STILL:
            still += 1
            ptp.append(0.0)
            continue
        try:
            reading = measure_dance(x.tolist(), track.fps, groove, start=track.start + a / track.fps, missing=True)
        except DanceMeasureError:
            continue
        readings.append(reading)
        ptp.append(reading.peak_to_peak)
    return readings, ptp, spans, still


def _locked(cycles: float) -> bool:
    return any(abs(cycles - lock) <= LOCK_TOLERANCE * lock for lock in LOCKS)


def _channel(track: BodyTrack, groove: Groove, chan: Channel, size: int, hop: int, gap: int) -> ChannelReading:
    if chan.name in ("hands.travel", "feet.travel"):
        return _travel(track, groove, chan)
    values, valid = channel(track, chan.name)
    runs = _runs(valid)
    level = Spread.of(values[valid])
    noise = _noise(values, runs)
    if not chan.groove:
        return ChannelReading(chan.name, chan.unit, chan.trust, int(valid.sum()), level, noise, *(0,) * 4, *(None,) * 5)
    windows = _windows(valid, size, hop, gap)
    readings, ptp, spans, still = _groove(values, windows, track, groove)
    locked = [r for r in readings if _locked(r.cycles_per_beat)]
    return ChannelReading(
        chan.name,
        chan.unit,
        chan.trust,
        int(valid.sum()),
        level,
        noise,
        len(windows),
        len(readings),
        still,
        len(locked),
        Spread.of(ptp),
        Spread.of(spans),
        Spread.of([r.cycles_per_beat for r in readings]),
        Spread.of([r.snap_ratio for r in readings]),
        Spread.of([r.hit_offset for r in locked]),
    )


def _travel(track: BodyTrack, groove: Groove, chan: Channel) -> ChannelReading:
    """Path length around the hips per beat, the place read every quarter beat between frames, both sides averaged."""
    ends = [p for p in chan.points if p.endswith(("wrist", "ankle"))]
    valid = track.seen[:, [_AT[p] for p in chan.points]].all(axis=1)
    quarter = groove.beat / 4 * track.fps  # frames
    per_beat = []
    for a, b in _runs(valid):
        marks = np.arange(a, b - 1, quarter)
        if len(marks) < 5:
            continue
        frames = np.arange(a, b)
        steps = []
        for end in ends:
            rel = track.points[a:b, _AT[end]] - _mid(track.points[a:b], "left_hip", "right_hip")
            place = np.stack([np.interp(marks, frames, rel[:, k]) for k in range(3)], axis=1)
            steps.append(np.linalg.norm(np.diff(place, axis=0), axis=1))
        step = np.mean(steps, axis=0)
        whole = len(step) // 4 * 4
        per_beat.extend(step[:whole].reshape(-1, 4).sum(axis=1).tolist())
    return ChannelReading(
        chan.name, chan.unit, chan.trust, int(valid.sum()), Spread.of(per_beat), None, *(0,) * 4, *(None,) * 5
    )


def _lag(track: BodyTrack, groove: Groove, lead: str, follow: str, size: int, hop: int, gap: int) -> LagReading:
    """The shift, within half a beat either way, at which ``follow``'s vertical speed best matches ``lead``'s, on the
    frames where both are seen; a peak correlation under ``MIN_CORRELATION`` reads no lag."""
    names = LAG_POINTS[lead] + LAG_POINTS[follow] + ("left_ankle", "right_ankle")
    valid = track.seen[:, [_AT[p] for p in names]].all(axis=1)
    heights = {key: np.mean([_height(track.points, p) for p in LAG_POINTS[key]], axis=0) for key in (lead, follow)}
    reach = max(1, round(0.5 * groove.beat * track.fps))
    shifts = np.arange(-reach, reach + 1)
    lags, peaks = [], []
    windows = _windows(valid, size, hop, gap)
    for a, b in windows:
        x, y = np.diff(heights[lead][a:b]), np.diff(heights[follow][a:b])
        both = valid[a : b - 1] & valid[a + 1 : b]
        x, y = np.where(both, x - np.mean(x[both]), 0.0), np.where(both, y - np.mean(y[both]), 0.0)
        corr = np.zeros(len(shifts))
        for n, k in enumerate(shifts.tolist()):
            u, v = x[max(0, -k) : len(x) - max(0, k)], y[max(0, k) : len(y) - max(0, -k)]
            pair = both[max(0, -k) : len(x) - max(0, k)] & both[max(0, k) : len(y) - max(0, -k)]
            scale = math.sqrt(float(np.dot(u[pair], u[pair]) * np.dot(v[pair], v[pair])))
            corr[n] = float(np.dot(u[pair], v[pair])) / scale if scale > STILL**2 else 0.0
        k = int(np.argmax(corr))
        if corr[k] < MIN_CORRELATION:
            continue
        fine = 0.0
        if 0 < k < len(corr) - 1:
            bend = corr[k - 1] - 2 * corr[k] + corr[k + 1]
            fine = 0.5 * (corr[k - 1] - corr[k + 1]) / bend if bend < 0 else 0.0
        lags.append((shifts[k] + fine) / track.fps / groove.beat)
        peaks.append(float(corr[k]))
    return LagReading(lead, follow, len(windows), len(lags), Spread.of(lags), Spread.of(peaks))


def measure_style(track: BodyTrack, groove: Groove) -> StyleReading:
    """Every channel and lag of ``track`` on ``groove``, the same way for a reference and for one of ours."""
    _bad(not isinstance(track, BodyTrack), "a style is measured on a BodyTrack", "track")
    _bad(not isinstance(groove, Groove), "a style is measured on a music.Groove", "groove")
    size = round(WINDOW_BEATS * groove.beat * track.fps)
    hop = max(1, round(HOP_BEATS * groove.beat * track.fps))
    gap = round(MAX_GAP_BEATS * groove.beat * track.fps)
    channels = {c.name: _channel(track, groove, c, size, hop, gap) for c in CHANNELS}
    lags = {f"{a}>{b}": _lag(track, groove, a, b, size, hop, gap) for a, b in LAGS}
    return StyleReading(
        groove.bpm,
        groove.offset,
        track.fps,
        track.frames,
        track.used,
        track.rejected,
        MappingProxyType(channels),
        MappingProxyType(lags),
    )


# --- one of ours as an estimator would record it -------------------------------------------------------------------


def pose_record(
    frames: Sequence[DanceFrame],
    fps: int,
    *,
    profile: sk.SkeletonProfile | None = None,
    source: str = "0" * 64,
    clamp: bool = True,
) -> dict:
    """A ``srstudio.pose-track/1.0.0`` record of one of our dances as a perfect estimator facing the dancer would write
    it: the study's round trip, and a record for tests and recipes that holds no real person. Landmarks the skeleton
    does not place (eyes, mouth, fingers, heels, toes) are put on the nearest point it does."""
    track = dance_body(frames, fps, profile=profile, clamp=clamp)
    metres = sk.preset(REFERENCE_PRESET).proportions.head_radius_m
    radius = 1.0  # head radii
    out = []
    for i, body in enumerate(track.points):
        place = {name: body[_AT[name]] for name in POINTS}
        across = _unit(_flat(place["right_hip"] - place["left_hip"]))
        front = _unit(np.cross(across, (0.0, 1.0, 0.0)))
        head = place["head"]
        place |= {"left_ear": head - across * radius, "right_ear": head + across * radius}
        rows = []
        for name in pt.LANDMARKS:
            if name in place:
                p = place[name]
            elif name.startswith(("left_heel", "right_heel", "left_foot", "right_foot")):
                p = place[f"{name.split('_')[0]}_ankle"]
            elif name.startswith(
                ("left_pinky", "right_pinky", "left_index", "right_index", "left_thumb", "right_thumb")
            ):
                p = place[f"{name.split('_')[0]}_wrist"]
            else:
                p = head + front * radius
            rows.append([round(float(v * metres * s), 5) for v, s in zip(p, (-1.0, 1.0, -1.0), strict=True)])
        image = [[round(0.5 + x / 4, 5), round(0.5 + y / 4, 5), 0.0, 0.99, 0.99] for x, y, _ in rows]
        out.append(
            {
                "index": i,
                "t_s": round(i / fps, 6),
                "image": image,
                "world": rows,
                "box": [0.25, 0.1, 0.75, 0.9],
                "position": 0.0,
                "appearance": 0.0,
            }
        )
    return {
        "schema": f"{pt.SCHEMA}/{pt.SCHEMA_VERSION}",
        "tool": "srstudio.dance_study.pose_record",
        "estimator": {
            "name": "srstudio-skeleton",
            "version": "1.0.0",
            "model": "forward kinematics",
            "model_sha256": "0" * 64,
            "licence": "none",
        },
        "source": {"sha256": source, "bytes": 1, "width": 1000, "height": 1000, "fps": float(fps), "frames": len(out)},
        "subject": {"pick": "central", "point": None, "first_frame": 0},
        "axes": dict(pt.AXES),
        "landmarks": list(pt.LANDMARKS),
        "start_frame": 0,
        "frames": out,
    }
