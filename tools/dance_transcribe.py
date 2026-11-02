#!/usr/bin/env python3
"""Transcribe measured dance moves into ``srstudio.dance-moves`` patterns on the shared skeleton (ADR 0212).

    python tools/dance_transcribe.py MOTION.json WINDOWS.json --out MOVES.json [--jobs 8] [--samples 16]

``MOTION.json`` is a ``dancepose.motion`` record (the dancepose SDK's output: per frame, per tracked person, the
15 joints and 13 auxiliary landmarks in metres from the hips, with the torso's yaw), kept outside the repository
because it is footage-derived pose of real people. ``WINDOWS.json`` is a ``srstudio.dance-windows`` document naming
each move to transcribe: a track, a start and an end in seconds, and how often the move was seen. Both are read
strictly and refused with a typed error at a path.

Each window becomes one ``dance.Move`` of ``LOOP_BEATS`` beats: the measured span is the strike onto the hit, the
rest of the loop the slow return. Every moved joint gets one sine pattern (bias, amplitude, phase and snap) fitted by
least squares on the realistic skeleton's forward kinematics against the measured 13-point body (hips, knees, ankles,
shoulders, elbows, wrists, head), hip-centred, facing removed, scaled so the torso is as long as the skeleton's. The
fit is bounded inside the tightest limits of every preset character, mirrored too, so the move dances on all of them
unclamped. The residual, in head radii, is written into the move's description: a transcription is lossy, and the
number says how lossy.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
(The pose estimator behind the record is a model too: its record is parsed and bounded here, never trusted.)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

import numpy as np
from scipy.optimize import least_squares

from srstudio import dance
from srstudio import dance_study as ds
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose
from srstudio.errors import SrstudioError
from srstudio.music import Groove

REPO = Path(__file__).resolve().parents[1]
TOOL = "tools/dance_transcribe.py"
MODEL = "Claude Fable 5.1 (claude-fable-5-1) in Claude Code"

MOTION_FORMAT = "dancepose.motion"
MOTION_VERSION = 1
WINDOWS_SCHEMA = re.compile(r"srstudio\.dance-windows/1\.(\d+)\.(\d+)\Z")
MAX_MOTION_BYTES = 256_000_000
MAX_WINDOWS_BYTES = 1_000_000
MAX_FRAMES = 100_000
MAX_PERSONS = 16
MAX_WINDOWS = 256
NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
JOINT_NAMES = ("head", "neck", "LS", "LE", "LW", "RS", "RE", "RW", "LH", "LK", "LA", "RH", "RK", "RA", "pelvis")
AUX_NAMES = (
    "nose", "left_ear", "right_ear", "left_index", "left_pinky", "left_thumb", "right_index", "right_pinky",
    "right_thumb", "left_heel", "left_foot_index", "right_heel", "right_foot_index",
)  # fmt: skip
PERSON_REQUIRED = (
    "track_id",
    "xy",
    "confidence",
    "torso_yaw_rad",
    "head_yaw_rad",
    "measured",
    "world_m",
    "aux_world_m",
)
PERSON_OPTIONAL = ("roll_rad", "roll_confidence", "aux_xy", "z_px")
POINT_OF = {  # the study's 13 points, by the record's joint names
    "left_hip": "LH", "right_hip": "RH", "left_knee": "LK", "right_knee": "RK", "left_ankle": "LA",
    "right_ankle": "RA", "left_shoulder": "LS", "right_shoulder": "RS", "left_elbow": "LE", "right_elbow": "RE",
    "left_wrist": "LW", "right_wrist": "RW",
}  # fmt: skip

LOOP_BEATS = 4.0  # the measured span fills the first half: the strike; the second half is the return
CYCLES = 1.0 / LOOP_BEATS
MIN_WINDOW_S, MAX_WINDOW_S = 0.25, 8.0
NEAREST_FRAMES = 3  # a sample may come from a frame this far from its time, when the tracker skipped a frame
MIN_TORSO_M, MAX_TORSO_M = 0.25, 1.2  # a hip-to-shoulder length outside this is no person
TORSO_SPREAD = 0.3  # a sample whose torso is this share off the window's median is a misread
MIN_AMPLITUDE = 0.02  # radians: below it a joint is held, not moved
MIN_BIAS = 0.02
HEAD_WEIGHT = 0.5  # the estimator places the head between the ears; the skeleton's centre differs
SNAP_RANGE = (0.15, 0.85)
TARGETS = (
    "hips.front_back", "hips.left_right", "hips.twist_left_right",
    "chest.front_back", "chest.left_right", "chest.twist_left_right",
    "neck.nod_down_up", "neck.tilt_left_right", "neck.turn_left_right",
    "left_upper_arm.down_up", "left_upper_arm.front_back", "left_upper_arm.twist_in_out", "left_lower_arm.stretch",
    "right_upper_arm.down_up", "right_upper_arm.front_back", "right_upper_arm.twist_in_out", "right_lower_arm.stretch",
    "left_upper_leg.front_back", "left_upper_leg.in_out", "left_lower_leg.stretch",
    "right_upper_leg.front_back", "right_upper_leg.in_out", "right_lower_leg.stretch",
)  # fmt: skip
REFERENCE_PRESET = "realistic"


class TranscribeError(SrstudioError, ValueError):
    """A motion record, a window list or a fit that cannot be used as given."""


def _bad(condition: bool, message: str, path: str) -> None:
    if condition:
        raise TranscribeError(message, path=path)


# --- strict readers --------------------------------------------------------------------------------------------------


def _no_constant(name: str) -> float:
    raise TranscribeError(f"{name} is not a number", path="$")


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        _bad(key in out, f"key {key!r} repeats", "$")
        out[key] = value
    return out


def _json(path: str | Path, most: int) -> object:
    try:
        with open(path, "rb") as handle:
            text = handle.read(most + 1)
    except OSError as error:
        raise TranscribeError(f"cannot read {path}: {error}", path=str(path)) from None
    _bad(len(text) > most, f"{path} is over {most} bytes", str(path))
    try:
        return json.loads(text.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_unique)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise TranscribeError(f"{path} is one JSON document: {error}", path=str(path)) from None


def _fields(value: object, path: str, required: tuple[str, ...], optional: tuple[str, ...] = ()) -> dict[str, object]:
    _bad(not isinstance(value, dict), f"{path} is an object", path)
    assert isinstance(value, dict)
    missing = [k for k in required if k not in value]
    _bad(bool(missing), f"{path} lacks {missing}", path)
    unknown = sorted(set(value) - set(required) - set(optional))
    _bad(bool(unknown), f"{path} has unknown fields {unknown}", path)
    return value


def _number(value: object, path: str, low: float = -math.inf, high: float = math.inf) -> float:
    _bad(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value),
        f"{path} is a finite number",
        path,
    )
    assert isinstance(value, (int, float))
    _bad(not low <= value <= high, f"{path} = {value} lies in {low}..{high}", path)
    return float(value)


def _whole(value: object, path: str, low: int, high: int) -> int:
    _bad(type(value) is not int or not low <= value <= high, f"{path} is a whole number in {low}..{high}", path)
    assert isinstance(value, int)
    return value


def _text(value: object, path: str, most: int = 512) -> str:
    _bad(not isinstance(value, str) or len(value) > most, f"{path} is text of at most {most} characters", path)
    assert isinstance(value, str)
    return value


def _matrix(value: object, path: str, rows: int, cols: int, low: float = -1e3, high: float = 1e3) -> np.ndarray:
    _bad(not isinstance(value, list) or len(value) != rows, f"{path} is a list of {rows} rows", path)
    assert isinstance(value, list)
    out = np.empty((rows, cols))
    for i, row in enumerate(value):
        _bad(not isinstance(row, list) or len(row) != cols, f"{path}[{i}] is a list of {cols} numbers", f"{path}[{i}]")
        for j, item in enumerate(row):
            out[i, j] = _number(item, f"{path}[{i}][{j}]", low, high)
    return out


@dataclass(frozen=True)
class Person:
    world: np.ndarray  # (15, 3) metres from the hips, the estimator's axes
    aux: np.ndarray  # (13, 3)
    yaw: float  # radians, 0 facing the camera, positive turned toward image right
    confidence: np.ndarray  # (15,)


@dataclass(frozen=True)
class Motion:
    fps: float
    times: np.ndarray
    persons: tuple[Mapping[str, Person], ...]

    def nearest(self, track: str, time: float) -> Person | None:
        """The track's pose at the frame nearest ``time``, within NEAREST_FRAMES frames; None when it was not seen."""
        order = np.argsort(np.abs(self.times - time), kind="stable")[: 2 * NEAREST_FRAMES + 2]
        for i in order:
            if abs(self.times[i] - time) > (NEAREST_FRAMES + 0.5) / self.fps:
                break
            found = self.persons[i].get(track)
            if found is not None:
                return found
        return None


def _person(value: object, path: str) -> Person:
    p = _fields(value, path, PERSON_REQUIRED, PERSON_OPTIONAL)
    _text(p["track_id"], f"{path}.track_id", 32)
    measured = _fields(p["measured"], f"{path}.measured", ("depth", "torso_yaw", "head_yaw", "axial_roll"))
    _bad(
        measured["depth"] is not True or measured["torso_yaw"] is not True,
        f"{path}.measured: depth and torso_yaw are measured, or the pose is 2D and cannot be transcribed",
        f"{path}.measured",
    )
    _matrix(p["xy"], f"{path}.xy", 15, 2, -1e5, 1e5)
    confidence = _matrix(
        [[c] for c in p["confidence"]] if isinstance(p["confidence"], list) else None, f"{path}.confidence", 15, 1, 0, 1
    )
    _number(p["head_yaw_rad"], f"{path}.head_yaw_rad", -2 * math.pi, 2 * math.pi)
    return Person(
        world=_matrix(p["world_m"], f"{path}.world_m", 15, 3, -5, 5),
        aux=_matrix(p["aux_world_m"], f"{path}.aux_world_m", 13, 3, -5, 5),
        yaw=_number(p["torso_yaw_rad"], f"{path}.torso_yaw_rad", -2 * math.pi, 2 * math.pi),
        confidence=confidence[:, 0],
    )


def read_motion(path: str | Path) -> Motion:
    """A ``dancepose.motion`` record, strictly: the fields this tool reads are checked, the others are named."""
    top = _fields(
        _json(path, MAX_MOTION_BYTES),
        "$",
        ("format", "format_version", "fps", "width", "height", "joint_names", "aux_landmark_names", "frames"),
        ("start_time", "source", "backend", "roll_segments", "conventions", "meta"),
    )
    _bad(top["format"] != MOTION_FORMAT, f"$.format is {MOTION_FORMAT!r}, not {top['format']!r}", "$.format")
    _bad(top["format_version"] != MOTION_VERSION, f"$.format_version is {MOTION_VERSION}", "$.format_version")
    fps = _number(top["fps"], "$.fps", 1, 240)
    _whole(top["width"], "$.width", 1, 16384)
    _whole(top["height"], "$.height", 1, 16384)
    _bad(top["joint_names"] != list(JOINT_NAMES), f"$.joint_names are {list(JOINT_NAMES)}", "$.joint_names")
    _bad(
        top["aux_landmark_names"] != list(AUX_NAMES),
        f"$.aux_landmark_names are {list(AUX_NAMES)}",
        "$.aux_landmark_names",
    )
    frames = top["frames"]
    _bad(
        not isinstance(frames, list) or not 1 <= len(frames) <= MAX_FRAMES,
        f"$.frames holds 1..{MAX_FRAMES} frames",
        "$.frames",
    )
    assert isinstance(frames, list)
    times = np.empty(len(frames))
    persons: list[Mapping[str, Person]] = []
    last_index = -1
    for i, frame in enumerate(frames):
        f = _fields(frame, f"$.frames[{i}]", ("frame", "time", "persons"))
        index = _whole(f["frame"], f"$.frames[{i}].frame", 0, 10 * MAX_FRAMES)
        _bad(index <= last_index, f"$.frames[{i}].frame = {index} does not follow {last_index}", f"$.frames[{i}].frame")
        last_index = index
        times[i] = _number(f["time"], f"$.frames[{i}].time", 0, 1e6)
        _bad(i > 0 and times[i] < times[i - 1], f"$.frames[{i}].time runs backward", f"$.frames[{i}].time")
        found = f["persons"]
        _bad(
            not isinstance(found, dict) or len(found) > MAX_PERSONS,
            f"$.frames[{i}].persons holds at most {MAX_PERSONS}",
            f"$.frames[{i}].persons",
        )
        assert isinstance(found, dict)
        here = {}
        for track, person in found.items():
            _bad(
                not isinstance(track, str) or not NAME.match(track),
                f"$.frames[{i}].persons: track {track!r} is a name",
                f"$.frames[{i}].persons",
            )
            here[track] = _person(person, f"$.frames[{i}].persons.{track}")
        persons.append(MappingProxyType(here))
    return Motion(fps, times, tuple(persons))


@dataclass(frozen=True)
class Window:
    name: str
    track: str
    start_s: float
    end_s: float
    seen: int
    dancers: int


def read_windows(path: str | Path) -> tuple[Window, ...]:
    """A ``srstudio.dance-windows`` document: the moves to transcribe, each named once."""
    top = _fields(_json(path, MAX_WINDOWS_BYTES), "$", ("schema", "source", "windows"), ("selection",))
    _bad(
        not isinstance(top["schema"], str) or not WINDOWS_SCHEMA.match(top["schema"]),
        "$.schema is srstudio.dance-windows/1.x",
        "$.schema",
    )
    source = _fields(
        top["source"], "$.source", ("title", "sha256"), ("youtube_id", "fps", "frames", "bpm", "extractor")
    )
    _text(source["title"], "$.source.title")
    _bad(
        not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]),
        "$.source.sha256 is 64 hex digits",
        "$.source.sha256",
    )
    if "selection" in top:
        _text(top["selection"], "$.selection", 2000)
    rows = top["windows"]
    _bad(
        not isinstance(rows, list) or not 1 <= len(rows) <= MAX_WINDOWS,
        f"$.windows holds 1..{MAX_WINDOWS} windows",
        "$.windows",
    )
    assert isinstance(rows, list)
    out: list[Window] = []
    names: set[str] = set()
    for i, row in enumerate(rows):
        path_i = f"$.windows[{i}]"
        w = _fields(row, path_i, ("name", "track", "start_s", "end_s", "seen", "dancers"))
        name = _text(w["name"], f"{path_i}.name", 64)
        _bad(not NAME.match(name), f"{path_i}.name {name!r} is a lowercase, hyphenated name", f"{path_i}.name")
        _bad(name in names, f"{path_i}.name {name!r} repeats", f"{path_i}.name")
        names.add(name)
        track = _text(w["track"], f"{path_i}.track", 32)
        _bad(not NAME.match(track), f"{path_i}.track {track!r} is a name", f"{path_i}.track")
        start, end = _number(w["start_s"], f"{path_i}.start_s", 0, 1e6), _number(w["end_s"], f"{path_i}.end_s", 0, 1e6)
        _bad(
            not MIN_WINDOW_S <= end - start <= MAX_WINDOW_S,
            f"{path_i}: a window lasts {MIN_WINDOW_S}..{MAX_WINDOW_S} s",
            path_i,
        )
        out.append(
            Window(
                name,
                track,
                start,
                end,
                _whole(w["seen"], f"{path_i}.seen", 1, 100_000),
                _whole(w["dancers"], f"{path_i}.dancers", 1, 1000),
            )
        )
    return tuple(out)


# --- the measured body -----------------------------------------------------------------------------------------------


def measured_body(motion: Motion, window: Window, samples: int) -> np.ndarray:
    """The window's dancer as ``samples`` bodies of the study's 13 points, in the skeleton's axes, hip-centred, the
    median facing removed and the torso as long as the skeleton's. Refused when the track is missing at a sample or
    the torso reads as no person."""
    _bad(type(samples) is not int or not 4 <= samples <= 64, "samples is a whole number in 4..64", "samples")
    joint = {name: i for i, name in enumerate(JOINT_NAMES)}
    aux = {name: i for i, name in enumerate(AUX_NAMES)}
    bodies, yaws = [], []
    for t in np.linspace(window.start_s, window.end_s, samples):
        person = motion.nearest(window.track, float(t))
        _bad(person is None, f"{window.name}: track {window.track} is not seen at {t:.3f} s", f"windows.{window.name}")
        assert person is not None
        points = np.array(
            [person.world[joint[POINT_OF[name]]] for name in ds.POINTS[:-1]]
            + [(person.aux[aux["left_ear"]] + person.aux[aux["right_ear"]]) / 2]
        )
        bodies.append(points * (-1.0, 1.0, -1.0))  # the estimator's axes to the skeleton's
        yaws.append(person.yaw)
    body = np.array(bodies)
    torso = ds._torso(body)
    _bad(
        not MIN_TORSO_M <= float(np.median(torso)) <= MAX_TORSO_M,
        f"{window.name}: torso of {np.median(torso):.2f} m is no person",
        f"windows.{window.name}",
    )
    _bad(
        float(np.max(np.abs(torso / np.median(torso) - 1))) > TORSO_SPREAD,
        f"{window.name}: a sample's torso is off the window's median by over {TORSO_SPREAD:.0%}",
        f"windows.{window.name}",
    )
    yaw = float(np.median(yaws))
    c, s = math.cos(yaw), math.sin(yaw)
    turn = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])
    body = body @ turn.T
    body = body - ds._mid(body, "left_hip", "right_hip")[:, None, :]
    return body * (ds.torso_head_radii() / float(np.median(ds._torso(body))))


# --- the fit ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Bounds:
    """Per target: the lowest and highest delta every preset character allows on top of its rest pose, the move's
    mirror included (a mirrored central dof changes sign; a mirrored limb dof lands on the other limb)."""

    low: dict[str, float]
    high: dict[str, float]


def _delta_limits(target: str) -> tuple[float, float]:
    """The delta range inside every preset's limits once added to that preset's rest pose."""
    los, his = [], []
    for name in sk.PRESETS:
        profile = sk.preset(name)
        if target not in profile.controls:
            continue
        low, high = profile.limits_of(target)
        rest = sk.rest_pose(profile).value(target)
        los.append(low - rest)
        his.append(high - rest)
    _bad(not los, f"{target}: no preset has it", target)
    return max(los), min(his)


def bounds() -> Bounds:
    low, high = {}, {}
    for target in TARGETS:
        lo, hi = _delta_limits(target)
        mirror_target, sign = dance.mirrored(target, 1.0)
        m_lo, m_hi = _delta_limits(mirror_target)
        if sign < 0:  # the mirrored value -v lies in the mirror target's range: v in [-m_hi, -m_lo]
            lo, hi = max(lo, -m_hi), min(hi, -m_lo)
        else:
            lo, hi = max(lo, m_lo), min(hi, m_hi)
        _bad(hi <= lo, f"{target}: no range every preset allows", target)
        low[target], high[target] = lo, hi
    return Bounds(low, high)


class Fitter:
    """Least squares from pattern parameters to the measured body through the skeleton's forward kinematics."""

    def __init__(self, body: np.ndarray, limits: Bounds) -> None:
        self.body = body
        self.limits = limits
        self.profile = sk.preset(REFERENCE_PRESET)
        rest = ds._skeleton_points(self.profile, sk.rest_pose(self.profile))
        self.scale = ds.torso_head_radii() / float(ds._torso(rest))
        self.u = np.linspace(0.0, 0.5, len(body))  # the measured span is the first half of the loop
        self.weight = np.ones((len(ds.POINTS), 1))
        self.weight[ds._AT["head"]] = HEAD_WEIGHT

    def values(self, params: np.ndarray, u: float) -> dict[str, float]:
        out = {}
        for k, target in enumerate(TARGETS):
            hit, far, phase, snap = params[4 * k : 4 * k + 4]
            out[target] = (hit + far) / 2 + (hit - far) / 2 * dance.wave("sine", snap, (u - phase) % 1.0)
        return out

    def points(self, params: np.ndarray) -> np.ndarray:
        out = np.empty_like(self.body)
        for i, u in enumerate(self.u):
            frame = dance.DanceFrame(
                0.0, (0.0, 0.0, 0.0), MappingProxyType(self.values(params, u)), None, frozenset(), "feet", None
            )
            here = ds._skeleton_points(self.profile, dance_pose(self.profile, frame, clamp=False).pose)
            out[i] = (here - ds._mid(here, "left_hip", "right_hip")) * self.scale
        return out

    def residual(self, params: np.ndarray) -> np.ndarray:
        return ((self.points(params) - self.body) * self.weight).ravel()

    def start(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The rest pose as parameters, and the bounds every preset allows: ``x0, low, high``."""
        n = len(TARGETS)
        lo = np.empty(4 * n)
        hi = np.empty(4 * n)
        x0 = np.empty(4 * n)
        for k, target in enumerate(TARGETS):
            low, high = self.limits.low[target], self.limits.high[target]
            lo[4 * k : 4 * k + 4] = (low, low, -0.5, SNAP_RANGE[0])
            hi[4 * k : 4 * k + 4] = (high, high, 0.5, SNAP_RANGE[1])
            rest = min(max(0.0, low), high)
            x0[4 * k : 4 * k + 4] = (rest, rest, 0.0, 0.5)
        return x0, lo, hi

    def rms(self, params: np.ndarray) -> float:
        """The unweighted distance left between the fitted and the measured body, in head radii."""
        return float(np.sqrt(np.mean((self.points(params) - self.body) ** 2)))

    def fit(self, max_nfev: int) -> tuple[np.ndarray, float]:
        _bad(
            type(max_nfev) is not int or not 1 <= max_nfev <= 1000, "max_nfev is a whole number in 1..1000", "max_nfev"
        )
        x0, lo, hi = self.start()
        result = least_squares(self.residual, x0, bounds=(lo, hi), max_nfev=max_nfev, diff_step=1e-3)
        return result.x, self.rms(result.x)


PLACES = 4  # decimals a written parameter keeps
MARGIN = 1e-5  # how far inside a bound a written extreme stays, so the sum with any rest pose rounds inside too


def _inward(value: float, low: float, high: float) -> float:
    """``value`` at PLACES decimals, pulled inside ``low..high`` by at least MARGIN; rounding never crosses a bound."""
    value = round(value, PLACES)
    step = 10.0**PLACES
    if value > high - MARGIN:
        value = math.floor((high - MARGIN) * step) / step
    if value < low + MARGIN:
        value = math.ceil((low + MARGIN) * step) / step
    _bad(not low <= value <= high, f"no value at {PLACES} places lies inside {low}..{high}", "bounds")
    return value


def _settle(hit: float, far: float, low: float, high: float) -> tuple[float, float]:
    """``bias, amplitude`` from the two written extremes, each kept inside ``low..high`` by :func:`_inward`; a swing
    too small to see becomes a hold at its middle, and a hold of nothing is nothing."""
    hit, far = _inward(hit, low, high), _inward(far, low, high)
    bias, amplitude = (hit + far) / 2, (hit - far) / 2
    if abs(amplitude) < MIN_AMPLITUDE:
        amplitude, bias = 0.0, _inward(bias, low, high)
    if abs(bias) < MIN_BIAS and low <= 0.0 <= high and amplitude == 0.0:
        bias = 0.0
    return bias, amplitude


def move_from(params: np.ndarray, window: Window, rms: float, limits: Bounds) -> dance.Move:
    """The fitted parameters as a standing move: both feet planted through the loop, a pattern per moved joint."""
    patterns = []
    for k, target in enumerate(TARGETS):
        hit, far, phase, snap = (float(v) for v in params[4 * k : 4 * k + 4])
        bias, amplitude = _settle(hit, far, limits.low[target], limits.high[target])
        if amplitude == 0.0 and bias == 0.0:
            continue
        if amplitude == 0.0:
            phase, snap = 0.0, 0.5
        patterns.append(
            dance.Pattern(
                target,
                amplitude,
                cycles=CYCLES,
                per="beat",
                phase=round(phase * LOOP_BEATS, 4),
                waveform="sine",
                snap=round(snap, 4),
                bias=bias,
            )
        )
    _bad(not patterns, f"{window.name}: nothing moved or held above {MIN_AMPLITUDE} rad", f"windows.{window.name}")
    moved = sorted(((abs(p.amplitude), p.target) for p in patterns if p.amplitude), reverse=True)[:3]
    parts = ", ".join(t.split(".")[0].replace("_", " ") for _, t in moved) or "a held pose"
    description = (
        f"FE!N {window.name}: {parts}. Seen {window.seen} times by {window.dancers} dancers; transcribed from "
        f"track {window.track} at {window.start_s:.2f}-{window.end_s:.2f} s, the strike over the first "
        f"{LOOP_BEATS / 2:g} beats of a {LOOP_BEATS:g}-beat loop, fit residual {rms:.2f} head radii."
    )
    return dance.Move(
        window.name,
        "feet",
        tuple(patterns),
        loop_beats=LOOP_BEATS,
        contacts=(dance.Contact("left_foot", 0.0, LOOP_BEATS), dance.Contact("right_foot", 0.0, LOOP_BEATS)),
        description=description,
    )


def transcribe(motion: Motion, window: Window, limits: Bounds, *, samples: int = 16, max_nfev: int = 80) -> dance.Move:
    """One window as a move, proved to dance unclamped on every preset character, mirrored too."""
    body = measured_body(motion, window, samples)
    params, rms = Fitter(body, limits).fit(max_nfev)
    move = move_from(params, window, rms, limits)
    prove(move)
    return move


def _extremes(move: dance.Move, beat: float) -> list[float]:
    """The seconds, inside one loop, at which each pattern is at its hit and at its far extreme."""
    times: list[float] = []
    for p in move.patterns:
        period = 1 / p.cycles_per_beat(4)
        for k in range(math.ceil(move.loop_beats / period * 2) + 1):
            t = (p.phase + k * period / 2) % move.loop_beats
            times.append(t * beat)
    return times


def prove(move: dance.Move, steps: int = 32) -> None:
    """The move and its mirror dance on every preset without clamping, at ``steps`` times a beat and at every
    pattern's own hit and far extreme, where a value sits closest to a limit."""
    grid = Groove(120)
    times = [step / steps * grid.beat for step in range(round(move.loop_beats * steps))] + _extremes(move, grid.beat)
    for name in sk.PRESETS:
        profile = sk.preset(name)
        for source in (move, move.mirror()):
            for t in times:
                try:
                    dance_pose(profile, dance.sample(source, grid, t), clamp=False)
                except SrstudioError as error:
                    raise TranscribeError(
                        f"{move.name} leaves {name}'s limits: {error}", path=f"moves.{move.name}"
                    ) from None


def resettled(move: dance.Move, limits: Bounds) -> dance.Move:
    """``move`` with every pattern's extremes pulled inside the bounds by this tool's current rule: what a document
    written under an earlier rule needs before it is kept on a resume. Then proved like a fresh fit."""
    patterns = []
    for p in move.patterns:
        _bad(
            p.target not in limits.low, f"{move.name}: {p.target} is not a target this tool fits", f"moves.{move.name}"
        )
        low, high = limits.low[p.target], limits.high[p.target]
        bias, amplitude = _settle(p.bias + p.amplitude, p.bias - p.amplitude, low, high)
        if amplitude == 0.0 and bias == 0.0:
            continue
        patterns.append(replace(p, bias=bias, amplitude=amplitude))
    _bad(not patterns, f"{move.name}: nothing is left of the move inside the bounds", f"moves.{move.name}")
    out = replace(move, patterns=tuple(patterns))
    prove(out)
    return out


# --- the document ----------------------------------------------------------------------------------------------------


def _pattern_record(p: dance.Pattern) -> dict[str, object]:
    out: dict[str, object] = {
        "target": p.target, "waveform": p.waveform, "cycles": p.cycles, "per": p.per, "phase": p.phase,
        "amplitude": p.amplitude, "snap": p.snap,
    }  # fmt: skip
    if p.bias:
        out["bias"] = p.bias
    return out


def document(moves: Sequence[dance.Move]) -> str:
    """The moves as a ``srstudio.dance-moves/1.0.0`` document, read back before it is returned."""
    records = []
    for m in moves:
        records.append(
            {
                "name": m.name,
                "description": m.description,
                "support": m.support,
                "loop_beats": m.loop_beats,
                "patterns": [_pattern_record(p) for p in m.patterns],
                "contacts": [{"foot": c.foot, "from": c.start, "to": c.end} for c in m.contacts],
            }
        )
    text = (
        json.dumps(
            {"schema": dance.MOVES_SCHEMA, "generated_by": {"tool": TOOL, "model": MODEL}, "moves": records}, indent=1
        )
        + "\n"
    )
    back = dance.parse_moves(text)
    _bad(tuple(back) != tuple(m.name for m in moves), "the written document does not read back as the moves", "$")
    for m in moves:
        _bad(back[m.name] != m, f"{m.name} does not read back as written", f"moves.{m.name}")
    return text


_SHARED: dict[str, object] = {}


def _share(motion: Motion, limits: Bounds) -> None:
    _SHARED["motion"], _SHARED["limits"] = motion, limits


def _one(args: tuple[Window, int, int]) -> tuple[str, dance.Move | None, str]:
    window, samples, max_nfev = args
    motion, limits = _SHARED["motion"], _SHARED["limits"]
    assert isinstance(motion, Motion) and isinstance(limits, Bounds)
    try:
        return window.name, transcribe(motion, window, limits, samples=samples, max_nfev=max_nfev), ""
    except SrstudioError as error:  # a refusal, or the skeleton's own: both name the window, neither is a crash
        return window.name, None, f"{type(error).__name__}: {error}"


def _progress(
    name: str, move: dance.Move | None, why: str, done: dict[str, dance.Move], refused: dict[str, str]
) -> None:
    if move is None:
        refused[name] = why
        print(f"dance_transcribe: refused {name}: {why}", file=sys.stderr)
    else:
        done[name] = move
        print(f"dance_transcribe: fitted {name}: {move.description.rsplit('residual', 1)[-1].strip()}", file=sys.stderr)


def run(
    motion_path: Path, windows_path: Path, out: Path, *, jobs: int, samples: int, max_nfev: int, resume: bool = False
) -> tuple[list[dance.Move], dict[str, str]]:
    """Transcribe every window into ``out``. With ``resume``, a window whose move ``out`` already holds is kept as
    written and not fitted again; the document is still written whole, in the windows' order."""
    motion = read_motion(motion_path)
    windows = read_windows(windows_path)
    limits = bounds()
    kept: Mapping[str, dance.Move] = {}
    if resume and out.exists():
        try:
            kept = dance.load_moves(out)
        except dance.DanceDataError as error:
            raise TranscribeError(f"cannot resume from {out}: {error}", path=str(out)) from None
    names = {w.name for w in windows}
    done: dict[str, dance.Move] = {}
    for name, old in kept.items():
        if name in names:
            try:
                done[name] = resettled(old, limits)
            except SrstudioError as error:
                raise TranscribeError(f"cannot resume {name} from {out}: {error}", path=f"moves.{name}") from None
    work = [(w, samples, max_nfev) for w in windows if w.name not in done]
    _share(motion, limits)
    refused: dict[str, str] = {}
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs, initializer=_share, initargs=(motion, limits)) as pool:
            for name, move, why in pool.map(_one, work):
                _progress(name, move, why, done, refused)
    else:
        for item in work:
            _progress(*_one(item), done, refused)
    moves = [done[w.name] for w in windows if w.name in done]
    _bad(
        not moves,
        "no window could be transcribed: " + "; ".join(f"{n}: {why}" for n, why in refused.items()),
        "$.windows",
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document(moves), encoding="utf-8")
    return moves, refused


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("motion", type=Path, help="a dancepose.motion record, outside the repository")
    parser.add_argument("windows", type=Path, help="a srstudio.dance-windows document")
    parser.add_argument("--out", type=Path, required=True, help="the srstudio.dance-moves document to write")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--samples", type=int, default=16, help="bodies fitted per window")
    parser.add_argument("--max-nfev", type=int, default=80, help="least-squares evaluations per window")
    parser.add_argument("--resume", action="store_true", help="keep the moves --out already holds, fit only the rest")
    args = parser.parse_args(argv)
    if not 1 <= args.jobs <= 64:
        print("dance_transcribe: --jobs lies in 1..64", file=sys.stderr)
        return 2
    try:
        moves, refused = run(
            args.motion,
            args.windows,
            args.out,
            jobs=args.jobs,
            samples=args.samples,
            max_nfev=args.max_nfev,
            resume=args.resume,
        )
    except TranscribeError as error:
        print(f"dance_transcribe: {error}", file=sys.stderr)
        return 1
    print(f"{args.out}: {len(moves)} moves, {len(refused)} refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
