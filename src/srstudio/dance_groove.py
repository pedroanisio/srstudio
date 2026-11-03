"""Full-body groove measures (ADR 0205): whether a dance on the floor moves the feet, the weight, the hips and the
chain above them, or carries the body about as one rigid block.

:func:`measure_groove` reads one :class:`dance_floor.Performance` frame by frame on its own skeleton:

- ``clearance``: in every whole bar, the most the lowest point of either sole (heel, ball or toe tip) rises off the
  floor; the reading is the least of the bars, in hip heights. A raised heel with the ball down clears nothing.
- ``weight_travel``: the centre of mass's sideways travel, peak to peak, over the mean distance across between the
  ankles: how far the weight moves from foot to foot.
- ``pelvis_yaw`` and ``pelvis_roll``: the hips' turn on the floor and their tilt across, peak to peak, radians.
- ``twist``: the shoulders' line turned on the hips' line on the floor, peak to peak: the dance study's
  ``torso.twist`` (ADR 0203), read the same way.
- ``counter``: the phase of the twist against the pelvis's turn, as a share of the pelvis's cycle in 0..0.5: 0 when
  the shoulders' line runs further round the way the hips turn, 0.5 when it turns back against them (counter-rotation).
  The study's dancer twists to alternate sides, so its peak to peak (``twist``) and this phase are read, never a mean.
- ``lags``: each link of the chain feet, knees, hips, chest, shoulders, neck, head after the one under it, sideways,
  in beats. Every link's phase is read on one cycle, the hips' (:func:`groove_cycle`), and the difference wrapped
  to half that cycle, so a link cannot read a whole cycle off; None for a link or its parent that does not move.
- ``loose``: the share of the upper body's motion (chest, shoulders, neck, head) that the hips do not carry, the root
  of its variance about the pelvis's frame over its variance in the world: 0 for one rigid block.
- ``jump``: for the ankles, the hips, the head and the centre of mass, the largest change of acceleration between
  neighbouring frames over that point's largest acceleration; the worst point. A jump in speed or acceleration at a
  plant or a lift reads near 1 or more; a smooth path at 200 frames a second reads a few hundredths per cycle.
- ``jerk``: the mean size of the third derivative of the root's path (the pelvis: ``hips`` is every skeleton's root)
  and of the centre of mass's, metres a second cubed at ``jerk_fps``; the larger of the two (GVHMR's "Jitter").
- ``pfc``: the physical foot contact score of EDGE (Tseng et al. 2023, arXiv 2211.10658, eqs. 9 and 10): the mean
  over frames of the centre of mass's acceleration, its downward part dropped, times each foot's speed, over the
  sequence's largest such acceleration. A centre of mass that accelerates along the floor must push on a foot that
  holds still. A foot's speed is its slower sole point, heel or ball, in hip heights a second, so a foot rocking on
  its ball counts as holding; 0 when one foot stands still throughout.
- ``slide_mm``: the farthest a held contact moves along the floor from where its hold began, millimetres: each
  foot's heel and toe, held while its footwork says (:attr:`FootGoal.contacts`) or, without footwork, while the foot
  is planted. ``slides`` keeps each contact's figure.

:class:`GrooveTarget` holds a reading to its ranges and names each miss; :data:`GROOVE` is the acceptance target.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from . import checks
from . import skeleton as sk
from ._dance_errors import DanceError
from ._floor_body import heading, sole
from .dance_floor import BALL_SHARE, FloorFrame, Performance
from .limbs.math3d import Frame, Vec3

__all__ = [
    "CHAIN",
    "GROOVE",
    "JERK_FPS",
    "GrooveError",
    "GrooveReading",
    "GrooveTarget",
    "contact_slide",
    "foot_contact",
    "groove_cycle",
    "mean_jerk",
    "measure_groove",
]

CHAIN = ("feet", "knees", "hips", "chest", "shoulders", "neck", "head")
UPPER = ("chest", "upper_chest", "neck", "head", "left_upper_arm", "right_upper_arm")
JERK_FPS = 200  # pictures a second the smoothness is read at: a 16th note at 120 BPM is 25 of them
STILL_M = 1e-4  # metres of sideways travel under which a link of the chain does not move
STILL_ACCELERATION = 0.01  # metres a second squared under which a point does not accelerate
CYCLES = (0.5, 1.0, 2.0, 4.0, 8.0)  # beats a groove's cycle may last: a dance repeats on the grid
STILL_RAD = 1e-4  # radians of turn under which the pelvis does not turn
CONTACTS = ("heel", "toe")
_ACROSS = Vec3(1.0, 0.0, 0.0)


class GrooveError(DanceError):
    """A performance that cannot be read as a groove: too short to hold a whole bar, or read at a bad rate."""


@dataclass(frozen=True)
class GrooveReading:
    """One performance's full-body groove (see the module's notes for each field)."""

    clearance: float
    weight_travel: float
    pelvis_yaw: float
    pelvis_roll: float
    twist: float
    counter: float | None
    lags: tuple[tuple[str, float | None], ...]
    loose: float
    jump: float
    jerk: float
    pfc: float
    slides: tuple[tuple[str, float], ...]

    @property
    def slide_mm(self) -> float:
        """The farthest any held contact slid, millimetres."""
        return max((v for _, v in self.slides), default=0.0)

    def lag(self, link: str) -> float | None:
        return dict(self.lags)[link]

    @property
    def chain_lag(self) -> float:
        """Beats the head runs after the hips: the links from the chest to the head, summed (moving links only)."""
        return sum(v for _, v in self.lags[CHAIN.index("chest") - 1 :] if v is not None)


def _soles(profile: sk.SkeletonProfile, side: str) -> dict[str, tuple[Vec3, ...]]:
    """The corners of a sole under the rest pose, in the frames of the segments that carry them: heel and ball on the
    foot, the toe tip on the toes when the foot has them."""
    rest = sk.rest_pose(profile)
    world = sk.world(profile, rest)
    half, heel, toe = sole(profile)
    ankle = world[f"{side}_foot"].origin
    floor = ankle.y + profile.length("ankle")
    toes = f"{side}_toes"
    ball_z = (world[toes].origin.z - ankle.z) if toes in world else BALL_SHARE * toe
    out: dict[str, tuple[Vec3, ...]] = {}
    for name, depths in ((f"{side}_foot", (-heel, ball_z)), (toes, (toe,))):
        if name not in world:
            continue
        frame = world[name]
        corners = (Vec3(ankle.x + dx, floor, ankle.z + dz) for dz in depths for dx in (-half, half))
        out[name] = tuple(frame.inverse_point(c) for c in corners)
    if toes not in world:
        out[f"{side}_foot"] += tuple(
            world[f"{side}_foot"].inverse_point(Vec3(ankle.x + dx, floor, ankle.z + toe)) for dx in (-half, half)
        )
    return out


def _yaw_of(a: Vec3, b: Vec3) -> float:
    """The turn on the floor of the line from ``a`` to ``b`` off the across axis, positive toward the right."""
    return math.atan2(-(b.z - a.z), b.x - a.x)


def _unwrap(values: list[float]) -> np.ndarray:
    return np.unwrap(np.asarray(values, dtype=float))


def _jump(points: np.ndarray, fps: int) -> float:
    """The largest change of acceleration between neighbouring frames over the largest acceleration, for one point's
    path (frames by 3); 0 for a point that does not accelerate."""
    if len(points) < 4:
        return 0.0
    acceleration = np.diff(points, n=2, axis=0) * fps * fps
    size = np.linalg.norm(acceleration, axis=1)
    top = float(np.max(size))
    if top < STILL_ACCELERATION:
        return 0.0
    return float(np.max(np.linalg.norm(np.diff(acceleration, axis=0), axis=1))) / top


def _harmonic(x: np.ndarray, times: np.ndarray, period_s: float) -> tuple[float, float]:
    """The size and the time of the peak, within one cycle, of ``x``'s first harmonic at ``period_s``: least squares,
    so a span of whole cycles less a frame reads it exactly."""
    turn = 2 * np.pi * times / period_s
    basis = np.column_stack((np.ones_like(times), np.cos(turn), np.sin(turn)))
    _, c, d = np.linalg.lstsq(basis, x, rcond=None)[0]
    return float(math.hypot(c, d)), float(math.atan2(d, c)) / (2 * np.pi) * period_s


def groove_cycle(x: Sequence[float] | np.ndarray, times: Sequence[float] | np.ndarray, beat_s: float) -> float:
    """The cycle, in beats, that a series repeats on: of :data:`CYCLES` that the span holds twice (less a frame),
    the one whose first harmonic explains most of the series. A dance repeats on the grid, so the cycle is chosen
    from it rather than read off a spectrum that two cycles cannot resolve. A still series, or one too short to hold
    the shortest cycle twice, raises :class:`GrooveError`."""
    values, at = np.asarray(x, float), np.asarray(times, float)
    if len(values) != len(at) or len(values) < 8:
        raise GrooveError("a cycle is read off at least 8 samples, one time each", path="x")
    if not (np.all(np.isfinite(values)) and np.all(np.isfinite(at)) and checks.number(beat_s) and beat_s > 0):
        raise GrooveError("a cycle is read off finite samples on a positive beat", path="x")
    spread = float(np.var(values))
    if spread <= 0:
        raise GrooveError("a still series has no cycle", path="x")
    step = float(np.median(np.diff(at)))
    span = float(at[-1] - at[0]) + step
    best, found = -1.0, None
    for beats in CYCLES:
        if span < 2 * beats * beat_s - 1e-6:
            continue
        size, _ = _harmonic(values, at, beats * beat_s)
        share = size * size / 2 / spread
        if share > best + 1e-9:
            best, found = share, beats
    if found is None:
        raise GrooveError(f"a span of {span:.3f} s holds no cycle of {CYCLES[0]:g} beat twice", path="x")
    return found


def _wrap(value: float, cycle: float) -> float:
    """``value`` wrapped into [-cycle / 2, cycle / 2)."""
    return value - cycle * math.floor(value / cycle + 0.5)


def _lags(across: dict[str, np.ndarray], times: np.ndarray, beat_s: float) -> list[tuple[str, float | None]]:
    """Each link after the one under it, beats: every phase on the hips' cycle, differences wrapped to half of it."""
    if np.ptp(across["hips"]) < STILL_M:
        return [(child, None) for child in CHAIN[1:]]
    cycle = groove_cycle(across["hips"], times, beat_s) * beat_s
    phase = {
        name: _harmonic(values, times, cycle)[1] if np.ptp(values) >= STILL_M else None
        for name, values in across.items()
    }
    out: list[tuple[str, float | None]] = []
    for parent, child in zip(CHAIN, CHAIN[1:], strict=False):
        a, b = phase[parent], phase[child]
        out.append((child, None if a is None or b is None else _wrap(b - a, cycle) / beat_s))
    return out


def _counter(yaw: np.ndarray, twist: np.ndarray, times: np.ndarray, beat_s: float) -> float | None:
    """The twist's phase against the pelvis's turn, a share of the pelvis's cycle in 0..0.5; None without a turn."""
    if np.ptp(yaw) < STILL_RAD or np.ptp(twist) < STILL_RAD:
        return None
    cycle = groove_cycle(yaw, times, beat_s) * beat_s
    lead = _harmonic(twist, times, cycle)[1] - _harmonic(yaw, times, cycle)[1]
    return abs(_wrap(lead, cycle)) / cycle


def measure_groove(run: Performance, *, fps: int = 50, jerk_fps: int = JERK_FPS) -> GrooveReading:
    """``run`` read as a full-body groove at ``fps`` pictures a second, and its smoothness at ``jerk_fps``, over its
    whole bars. A performance under one whole bar raises :class:`GrooveError`; a seated one reads its feet resting."""
    if not isinstance(run, Performance):
        raise GrooveError(f"a groove is read off a dance_floor.Performance, not {type(run).__name__}", path="run")
    for name, value in (("fps", fps), ("jerk_fps", jerk_fps)):
        if type(value) is not int or not 10 <= value <= 240:
            raise GrooveError(f"{name} {value!r} is a whole number in 10..240", path=name)
    profile, groove = run.profile, run.groove
    bar_s = groove.beat * groove.beats_per_bar
    bars = math.floor((run.end_s - run.start_s) / bar_s + 1e-9)
    if bars < 1:
        raise GrooveError("a groove is read over at least one whole bar", path="run")
    frames = _whole(run, fps, bars * bar_s)
    spot = run.spot.frame()
    height = profile.pelvis_height
    if not all(profile.has(f"{side}_foot") for side in ("left", "right")):
        raise GrooveError("a groove is read off a skeleton with both feet", path="run")
    soles = {side: _soles(profile, side) for side in ("left", "right")}
    floor = run.floor_y

    clear = [0.0] * bars
    times = np.asarray([f.time for f in frames])
    com_x, width = [], []
    hips_yaw, hips_roll, twist = [], [], []
    across: dict[str, list[float]] = {name: [] for name in CHAIN}
    upper_world: list[list[Vec3]] = []
    upper_local: list[list[Vec3]] = []
    for f in frames:  # bounded by Performance.frames
        world = sk.world(profile, f.pose)
        local = {k: spot.inverse_point(v.origin) for k, v in world.items()}
        bar = math.floor((f.time - run.start_s) / bar_s + 1e-9)
        if 0 <= bar < bars:
            for segments in soles.values():
                lowest = max(world[name].point(c).y for name, cs in segments.items() for c in cs)
                clear[bar] = max(clear[bar], (floor - lowest) / height)
        com_x.append(spot.inverse_point(f.com).x)
        width.append(abs(local["right_foot"].x - local["left_foot"].x))
        hips = world["hips"]
        facing = heading(spot.rotation)
        hips_yaw.append(heading(hips.rotation) - facing)
        hips_roll.append(math.asin(max(-1.0, min(1.0, hips.rotation.rotate(_ACROSS).y))))
        pelvis = _yaw_of(local["left_upper_leg"], local["right_upper_leg"])
        line = _yaw_of(local["left_upper_arm"], local["right_upper_arm"])
        twist.append(line - pelvis)
        crown = world["head"].point(profile.tip("head") or Vec3())
        head = (world["head"].origin + crown) * 0.5
        steps = run.frame(f.time).steps
        load = 0.5 if steps is None else steps.weight
        points = {
            "feet": (1 - load) * local["left_foot"].x + load * local["right_foot"].x,
            "knees": (1 - load) * local["left_lower_leg"].x + load * local["right_lower_leg"].x,
            "hips": local["hips"].x,
            "chest": local["chest"].x,
            "shoulders": (local["left_upper_arm"].x + local["right_upper_arm"].x) / 2,
            "neck": local["neck"].x,
            "head": spot.inverse_point(head).x,
        }
        for name in CHAIN:
            across[name].append(points[name])
        moving = [world[name].origin for name in UPPER] + [head]
        upper_world.append(moving)
        upper_local.append([hips.inverse_point(p) for p in moving])

    yaw, turned = _unwrap(hips_yaw), _unwrap(twist)
    track = _track(frames, run, soles)
    lags = _lags({name: np.asarray(values) for name, values in across.items()}, times, groove.beat)
    return GrooveReading(
        clearance=min(clear),
        weight_travel=float(np.ptp(com_x)) / max(float(np.mean(width)), 1e-9),
        pelvis_yaw=float(np.ptp(yaw)),
        pelvis_roll=float(np.ptp(hips_roll)),
        twist=float(np.ptp(turned)),
        counter=_counter(yaw, turned, times, groove.beat),
        lags=tuple(lags),
        loose=_loose(upper_world, upper_local, frames),
        jump=_smoothness(run, jerk_fps, bars * bar_s),
        jerk=_root_jerk(run, jerk_fps, bars * bar_s),
        pfc=foot_contact(np.asarray([(c.x, c.y, c.z) for c in (f.com for f in frames)]), track, fps, scale=height),
        slides=_slides(run, frames, track),
    )


def _whole(run: Performance, fps: int, span_s: float) -> tuple[FloorFrame, ...]:
    """The performance's frames in its whole bars: the frame at its end, where the dance has stopped, is left out."""
    return tuple(f for f in run.frames(fps) if f.time < run.start_s + span_s - 1e-9)


def _loose(world: list[list[Vec3]], local: list[list[Vec3]], frames: Sequence[object]) -> float:
    """The root of the upper body's variance about the pelvis's frame over its variance in the world."""
    w = np.asarray([[(p.x, p.y, p.z) for p in row] for row in world])
    loc = np.asarray([[(p.x, p.y, p.z) for p in row] for row in local])
    moved = float(np.sum(np.var(w, axis=0)))
    if moved < 1e-12:
        return 0.0
    return math.sqrt(float(np.sum(np.var(loc, axis=0))) / moved)


def _smoothness(run: Performance, fps: int, span_s: float) -> float:
    profile = run.profile
    tracks: dict[str, list[tuple[float, float, float]]] = {}
    for f in _whole(run, fps, span_s):  # bounded by Performance.frames
        world = sk.world(profile, f.pose)
        crown = world["head"].point(profile.tip("head") or Vec3())
        head = (world["head"].origin + crown) * 0.5
        named = {"hips": world["hips"].origin, "head": head, "com": f.com}
        for side in ("left", "right"):
            if f"{side}_foot" in world:
                named[f"{side}_ankle"] = world[f"{side}_foot"].origin
        for key, p in named.items():
            tracks.setdefault(key, []).append((p.x, p.y, p.z))
    return max(_jump(np.asarray(points), fps) for points in tracks.values())


def _root_jerk(run: Performance, fps: int, span_s: float) -> float:
    """The larger mean jerk, metres a second cubed, of the root (the pelvis) and the centre of mass."""
    hips, com = [], []
    for f in _whole(run, fps, span_s):  # bounded by Performance.frames
        root = f.pose.root.origin
        hips.append((root.x, root.y, root.z))
        com.append((f.com.x, f.com.y, f.com.z))
    return max(mean_jerk(np.asarray(hips), fps), mean_jerk(np.asarray(com), fps))


Soles = dict[str, dict[str, tuple[Vec3, ...]]]


def _points(world: Mapping[str, Frame], soles: Soles, side: str) -> tuple[Vec3, Vec3]:
    """``side``'s heel and toe this frame, the points a foot pitches and turns about: the middle of the heel's
    corners, and the ball: the toes' joint, or on a foot without toes the sole under its ball. (The toe tip swings
    round the ball in a pivot, and the sole under the toes' joint rolls as the heel rises: neither holds still.)"""
    foot, toes = f"{side}_foot", f"{side}_toes"
    heel_l, heel_r, ball_l, ball_r = soles[side][foot][:4]
    heel = (world[foot].point(heel_l) + world[foot].point(heel_r)) * 0.5
    if toes in world:
        return heel, world[toes].origin
    return heel, (world[foot].point(ball_l) + world[foot].point(ball_r)) * 0.5


def _track(frames: Sequence[FloorFrame], run: Performance, soles: Soles) -> np.ndarray:
    """Both feet's heel and toe over ``frames``: frames by side (left, right) by contact (heel, toe) by xyz, metres."""
    out = []
    for f in frames:  # bounded by Performance.frames
        world = sk.world(run.profile, f.pose)
        out.append([[(p.x, p.y, p.z) for p in _points(world, soles, side)] for side in ("left", "right")])
    return np.asarray(out, float)


def foot_contact(com: np.ndarray, feet: np.ndarray, fps: int, *, scale: float = 1.0) -> float:
    """EDGE's physical foot contact score (Tseng et al. 2023, eqs. 9 and 10) of a centre of mass's path ``com``
    (frames by xyz, y down) over feet ``feet`` (frames by 2 feet by contact points by xyz) at ``fps``: per frame, the
    centre of mass's acceleration with its downward part dropped, times each foot's speed (its slowest contact
    point's, over ``scale`` metres a second); averaged over the frames and divided by the largest such acceleration.
    0 while a foot holds still; a centre of mass driven about by skating feet reads high. Paths of unequal length,
    under 3 frames, or holding a value that is not finite raise :class:`GrooveError`."""
    com, feet = np.asarray(com, float), np.asarray(feet, float)
    if com.ndim != 2 or com.shape[1] != 3 or feet.ndim != 4 or feet.shape[1] != 2 or feet.shape[3] != 3:
        raise GrooveError("foot contact reads a path of frames by xyz and feet of frames by 2 by points by xyz")
    if len(com) != len(feet) or len(com) < 3:
        raise GrooveError("foot contact reads two paths of one length, 3 frames or more")
    if not (np.all(np.isfinite(com)) and np.all(np.isfinite(feet))) or type(fps) is not int or fps < 1:
        raise GrooveError("foot contact reads finite paths at a whole number of frames a second")
    acceleration = (com[2:] - 2 * com[1:-1] + com[:-2]) * fps * fps
    acceleration[:, 1] = np.minimum(acceleration[:, 1], 0.0)  # y points down: only an upward push needs a foot
    size = np.linalg.norm(acceleration, axis=1)
    top = float(np.max(size))
    if top < STILL_ACCELERATION:
        return 0.0
    speed = np.linalg.norm(feet[2:] - feet[:-2], axis=3) * fps / 2 / scale  # central differences
    slowest = speed.min(axis=2)
    return float(np.mean(size * slowest[:, 0] * slowest[:, 1])) / top


def contact_slide(points: np.ndarray, held: Sequence[bool]) -> float:
    """The farthest a contact point (frames by xyz, metres, y down) moves along the floor from where each hold began,
    over the frames where ``held``; millimetres. A path and flags of unequal length raise :class:`GrooveError`."""
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) != len(held) or not np.all(np.isfinite(points)):
        raise GrooveError("a slide is read off a finite path of frames by xyz and one flag a frame")
    worst, first = 0.0, None
    for here, on in zip(points, held, strict=True):  # bounded by the path
        if not on:
            first = None
        elif first is None:
            first = here
        else:
            worst = max(worst, math.hypot(here[0] - first[0], here[2] - first[2]) * 1000)
    return worst


def mean_jerk(points: np.ndarray, fps: int) -> float:
    """The mean size of a path's third derivative (frames by xyz, metres, at ``fps``), metres a second cubed."""
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.all(np.isfinite(points)) or type(fps) is not int:
        raise GrooveError("jerk is read off a finite path of frames by xyz at a whole number of frames a second")
    if len(points) < 4:
        return 0.0
    return float(np.mean(np.linalg.norm(np.diff(points, n=3, axis=0), axis=1))) * fps**3


def _held(run: Performance, frame: FloorFrame, side: str) -> tuple[bool, bool]:
    """Whether ``side``'s heel and toe hold still at ``frame``: as its footwork says, else while it is planted."""
    steps = run.frame(frame.time).steps
    if steps is not None:
        return steps.contacts(side)
    planted = f"{side}_foot" in frame.planted
    return (planted, planted)


def _slides(run: Performance, frames: Sequence[FloorFrame], track: np.ndarray) -> tuple[tuple[str, float], ...]:
    """Each foot's heel and toe (``track``, from :func:`_track`): the farthest it moved along the floor from where a
    hold began, millimetres."""
    out = []
    for n, side in enumerate(("left", "right")):
        held = [_held(run, f, side) for f in frames]
        for k, part in enumerate(CONTACTS):
            out.append((f"{side}_{part}", contact_slide(track[:, n, k], [h[k] for h in held])))
    return tuple(out)


@dataclass(frozen=True)
class GrooveTarget:
    """The ranges a full-body groove holds (ADR 0205): ``clearance`` the least a foot clears the floor each bar,
    hip heights; ``weight_travel`` the least share of the stance the weight travels; ``pelvis_yaw``, ``pelvis_roll``
    and ``twist`` ranges in radians; ``counter`` the least share of a cycle the twist runs against the hips' turn;
    each link of the chain no more than ``lag_slack`` beats ahead of its parent, and the head ``chain_lag`` beats
    after the hips at least; ``loose`` the least share of loose upper-body motion; ``jump`` the most; ``jerk`` the
    most mean jerk of the root, metres a second cubed; ``pfc`` the most physical foot contact score; ``slide_mm`` the
    farthest a held heel or toe may slide."""

    clearance: float = 0.05
    weight_travel: float = 0.5
    pelvis_yaw: tuple[float, float] = (0.2, 0.8)
    pelvis_roll: tuple[float, float] = (0.1, 0.5)
    twist: tuple[float, float] = (0.0955, 0.376)
    counter: float = 0.35
    lag_slack: float = 0.02
    chain_lag: float = 0.04
    loose: float = 0.2
    jump: float = 0.35
    jerk: float = 500.0
    pfc: float = 0.01
    slide_mm: float = 1.0

    def misses(self, reading: GrooveReading) -> tuple[str, ...]:
        """Each way ``reading`` falls outside the target, named; empty when it holds."""
        out = []
        if reading.clearance < self.clearance:
            out.append(f"clearance {reading.clearance:.3f} hip heights, under {self.clearance:g} in some bar")
        if reading.weight_travel < self.weight_travel:
            out.append(f"weight travel {reading.weight_travel:.2f} of the stance, under {self.weight_travel:g}")
        for name in ("pelvis_yaw", "pelvis_roll", "twist"):
            low, high = getattr(self, name)
            value = getattr(reading, name)
            if not low <= value <= high:
                out.append(f"{name.replace('_', ' ')} {value:.3f} rad, not {low:g}..{high:g}")
        if reading.counter is None or reading.counter < self.counter:
            found = "none" if reading.counter is None else f"{reading.counter:.2f}"
            out.append(f"twist against the hips' turn {found} of a cycle, under {self.counter:g}")
        for link, lag in reading.lags:
            if lag is not None and lag < -self.lag_slack:
                out.append(f"{link} leads the link under it by {-lag:.3f} beat")
        if reading.chain_lag < self.chain_lag:
            out.append(f"head {reading.chain_lag:.3f} beat after the hips, under {self.chain_lag:g}")
        if reading.loose < self.loose:
            out.append(f"loose upper body {reading.loose:.2f}, under {self.loose:g}: one rigid block")
        if reading.jump > self.jump:
            out.append(f"acceleration jumps {reading.jump:.2f} of its peak between frames, over {self.jump:g}")
        if reading.jerk > self.jerk:
            out.append(f"root jerk {reading.jerk:.1f} m/s3, over {self.jerk:g}")
        if reading.pfc > self.pfc:
            out.append(f"physical foot contact {reading.pfc:.4f}, over {self.pfc:g}: the weight moves on moving feet")
        if reading.slide_mm > self.slide_mm:
            out.append(f"a held contact slid {reading.slide_mm:.2f} mm, over {self.slide_mm:g}")
        return tuple(out)


GROOVE = GrooveTarget()
