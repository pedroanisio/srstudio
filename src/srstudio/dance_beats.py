"""How well a dance's stops land on its music's beats, scored as AIST++ scores it (ADR 0204).

Li, Yang, Ross and Kanazawa, "AI Choreographer: Music Conditioned 3D Dance Generation with AIST++", ICCV 2021,
Eq. 2: the kinematic beats are the local minima of the body's kinetic velocity, and each is scored by a Gaussian of
its distance to the nearest music beat, ``exp(-d^2 / (2 sigma^2))`` with ``sigma = 3`` frames at 60 fps, averaged over
the kinematic beats. Siyao et al., "Bailando: 3D Dance Generation by Actor-Critic GPT with Choreographic Memory",
CVPR 2022, Eq. 15, averages over the music beats instead, each scored against its nearest kinematic beat. Both are
kept here, in seconds, so a take at any frame rate reads the same. The kinetic velocity is the mean of the body's
points' speeds, as in Bailando's published code.

That code also smooths the velocity with a Gaussian of ``sigma = 5`` frames at 60 fps (:data:`SMOOTH`) before finding
its minima. Neither paper states it, and it is off by default: a gesture that strikes onto its hit and eases away has
a lopsided speed around the stop, and the smoothing drags the stop toward the slow side. At 120 BPM our ``clap``
stops 0.15 beat late once smoothed, and Bailando's score then reads it better half a beat off the music than on it.

A beat is where the body stops, not which way it was going: a sine that turns once a beat stops at both of its
extremes, half a beat apart, and reads the same shifted by half a beat. A held body has no local minimum, so no
kinematic beat, and scores 0, as the reference code does; a hold between two moves is one stop, at the hold's
middle, where ``scipy.signal.argrelextrema`` would find none.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter1d

from . import skeleton as sk
from ._dance_measure import DanceMeasureError
from .music import Groove

SIGMA = 3 / 60  # seconds: sigma = 3 frames at 60 fps (AIST++ Eq. 2, Bailando Eq. 15)
SMOOTH = 5 / 60  # seconds: Bailando's code smooths the kinetic velocity with sigma = 5 frames at 60 fps; off here
OVER = ("dance", "music")
MIN_FRAMES = 3
MAX_FPS = 1000
TIE = 1e-9  # of the take's top speed: two speeds closer than this are one


def _lows(speed: np.ndarray) -> list[float]:
    """The strict local minima of ``speed`` as sample indices. A flat bottom, equal speeds lower than both sides, is
    one minimum at its middle: a stop that falls exactly between two samples measures the same speed on both."""
    tie = TIE * float(np.max(speed)) if speed.size else 0.0
    out, i, n = [], 0, len(speed)
    while i < n:
        j = i
        while j + 1 < n and abs(speed[j + 1] - speed[i]) <= tie:
            j += 1
        if i > 0 and j < n - 1 and speed[i - 1] - speed[i] > tie and speed[j + 1] - speed[j] > tie:
            out.append((i + j) / 2)
        i = j + 1
    return out


def _bad(condition: bool, message: str, path: str) -> None:
    if condition:
        raise DanceMeasureError(message, code="dance.measure", path=path)


def _times(values: object, path: str) -> tuple[float, ...]:
    _bad(isinstance(values, (str, bytes)) or not isinstance(values, Sequence), f"{path} is a sequence of seconds", path)
    assert isinstance(values, Sequence)
    out = tuple(values)
    _bad(not all(isinstance(t, (int, float)) and math.isfinite(t) for t in out), f"{path} are finite seconds", path)
    _bad(any(b < a for a, b in zip(out, out[1:], strict=False)), f"{path} are in order", path)
    return tuple(float(t) for t in out)


def beat_align(dance: Sequence[float], music: Sequence[float], *, sigma: float = SIGMA, over: str = "dance") -> float:
    """The beat alignment score of kinematic beats ``dance`` against ``music`` beats, both in seconds: the AIST++
    score averaged over the dance's beats (``over="dance"``) or Bailando's over the music's (``over="music"``)."""
    kinematic, beats = _times(dance, "dance"), _times(music, "music")
    _bad(not beats, "a score needs at least one music beat", "music")
    _bad(not (isinstance(sigma, (int, float)) and math.isfinite(sigma) and sigma > 0), "sigma is positive", "sigma")
    _bad(over not in OVER, f"over is one of {OVER}", "over")
    if not kinematic:
        return 0.0
    scored, against = (kinematic, beats) if over == "dance" else (beats, kinematic)
    near = np.asarray(against)
    total = sum(math.exp(-float(np.min((near - t) ** 2)) / (2 * sigma**2)) for t in scored)
    return total / len(scored)


def kinematic_beats(points: object, fps: int, *, start: float = 0.0, smooth: float = 0.0) -> tuple[float, ...]:
    """The seconds at which the body's speed has a strict local minimum: ``points`` is ``(frames, points, 3)``
    positions, the first frame at ``start``. The speed is the mean of the points' speeds, as measured or smoothed by
    a Gaussian of ``smooth`` seconds (:data:`SMOOTH` is Bailando's); each speed sits midway between its two frames."""
    _bad(not isinstance(points, np.ndarray), "points is a numpy array of positions", "points")
    assert isinstance(points, np.ndarray)
    _bad(points.ndim != 3 or points.shape[2] != 3, "points is (frames, points, 3)", "points")
    _bad(points.shape[0] < MIN_FRAMES or points.shape[1] < 1, f"points holds {MIN_FRAMES} frames or more", "points")
    _bad(not np.all(np.isfinite(points)), "points are finite", "points")
    _bad(not (type(fps) is int and 1 <= fps <= MAX_FPS), f"fps is a whole number in 1..{MAX_FPS}", "fps")
    _bad(not (isinstance(start, (int, float)) and math.isfinite(start)), "start is a finite second", "start")
    _bad(not (isinstance(smooth, (int, float)) and math.isfinite(smooth) and smooth >= 0), "smooth >= 0", "smooth")
    speed = np.mean(np.linalg.norm(np.diff(points.astype(float), axis=0), axis=2), axis=1) * fps
    if smooth > 0:
        speed = gaussian_filter1d(speed, smooth * fps)
    return tuple(float(start + (i + 0.5) / fps) for i in _lows(speed))


@dataclass(frozen=True)
class BeatAlignment:
    """A take's beat alignment: ``score`` as AIST++ averages it, over the ``kinematic`` beats; ``music_score`` as
    Bailando averages it, over the ``music`` beats inside the take; both beat lists in seconds."""

    score: float
    music_score: float
    kinematic: tuple[float, ...]
    music: tuple[float, ...]


def beat_alignment(points: object, fps: int, groove: Groove, *, start: float = 0.0) -> BeatAlignment:
    """``points`` (see :func:`kinematic_beats`) scored against ``groove``'s beats over the take."""
    _bad(not isinstance(groove, Groove), "groove is a Groove", "groove")
    kinematic = kinematic_beats(points, fps, start=start)
    assert isinstance(points, np.ndarray)
    end = start + (points.shape[0] - 1) / fps
    music = tuple(groove.between(start, end + 1e-9))
    return BeatAlignment(beat_align(kinematic, music), beat_align(kinematic, music, over="music"), kinematic, music)


def body_points(profile: sk.SkeletonProfile, pose: sk.SkeletonPose) -> np.ndarray:
    """Every joint and every bone's end of ``pose`` in world space, in metres, as ``(points, 3)``: a head that nods
    moves its crown though its joint stays put."""
    frames = sk.world(profile, pose)
    found = [frame.origin for frame in frames.values()] + list(sk.tips(profile, pose).values())
    return np.array([(p.x, p.y, p.z) for p in found], dtype=float)
