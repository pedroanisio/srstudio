"""Comic craft, measured: the camera moves an episode makes and the pauses between its spoken lines.

Where the camera is and when nobody speaks are part of a joke (crash zooms, punch-ins on the cut, slow pushes,
the awkward pause). :func:`moves` reads them from the scene: every uniform scale change (``scaleX`` and ``scaleY``
alike, so a spin or a stretch is not a zoom) of at least 15 % on a group, told apart by speed (a hold key or a step
under :data:`CUT` is a punch-in on the cut, :data:`~srstudio.camera.SNAP` or faster is a crash zoom, slower a push)
and marked as the camera when the group is a location, an angle, a shot or a setup.
:func:`pauses` finds the silences between the lines of ``dialogue.json``, ``narration.json`` or a takes
``timeline.json``, and :func:`levels` measures the rendered sound inside each one, so a pause meant to be awkward is
shown to be quiet, or filled. :func:`opening_silences` measures the first seconds as well, where :func:`pauses` is
blind to the wait before the first line. :func:`holding` lists every stretch of a render that stands still.
:func:`crowded` lists the lines that start with no breath after the one before, which :func:`pauses` cannot see.
:func:`flashing` lists every stretch of a render that flashes, where the strict encode's check names only the first; it
says where to look, and the encode stays the verdict.
``srstudio craft`` prints the report (schema :data:`SCHEMA`).
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from . import checks
from .camera import SNAP
from .errors import SrstudioError

DOUBLED = 0.001  # seconds of shared band below any frame, so a rounded time is not an overlap

__all__ = [
    "Hold",
    "SCHEMA",
    "CUT",
    "MIN_RATIO",
    "PAUSE",
    "QUIET_DB",
    "CraftError",
    "Move",
    "Pause",
    "Craft",
    "doubled_captions",
    "moves",
    "STATEMENT_BY",
    "lines",
    "pauses",
    "opening_silences",
    "clipped",
    "Statement",
    "statement",
    "levels",
    "luminance",
    "flashing",
    "holding",
    "measure",
]

SCHEMA = "1.5.0"  # 1.1.0: the opening's silences; 1.2.0: where a render flashes; 1.3.0: where it holds still;
# 1.4.0: the lines a recording cut short
CUT = 1 / 60  # a step faster than half a frame at 30 fps is a cut, not a move
MIN_RATIO = 0.15  # a scale change smaller than this is a breath or a squash, not a move
STATEMENT_BY = 3.0  # seconds: the first statement is finished by here, so the trouble is clear by second 3
PAUSE = 0.8  # seconds between lines that count as a pause
BREATH = 0.15  # seconds: a line that starts sooner than this after the last one runs into it
OPENING = 5.0  # seconds of a reel that have to hold a stranger
OPENING_LIMIT = 1.0  # seconds without a line that the opening can afford
QUIET_DB = -35.0  # mean level at or under which a pause is quiet: no music or effect fills it
FLOOR_DB = -120.0  # how digital silence (-inf) is written in the JSON report
SCAN_WIDTH, SCAN_HEIGHT = 108, 192  # the picture is scanned this small: a flash is large by definition
FLASHES_A_SECOND = 3  # the guideline's limit; a flash is a pair of opposing swings
SWING = 0.1  # of white, in linear light: the least a swing can be
BRIGHT = 0.8  # of white: a swing whose darker side is at or above this does not count
FLASH_SHARE = 0.05  # of the picture over the limit in one second, from which a stretch is worth listing
HOLD_LEAST = 1.0  # seconds a picture must stand to be listed
HOLD_CHANGE = 0.01  # of white, in linear light: more than an encoder repaints at a keyframe
HOLD_SHARE = 0.002  # of the picture changed, past which it no longer stands
CAMERA = re.compile(r"location-.+|.+-angle|shot-.+|setup-.+")
_MEAN = re.compile(r"mean_volume:\s*(-?inf|-?\d+(?:\.\d+)?) dB")
_run = subprocess.run


class CraftError(SrstudioError, ValueError):
    """A scene, a line file or a measurement that cannot be read."""


@dataclass(frozen=True)
class Move:
    """A change of framing: ``kind`` is ``punch-in``, ``crash`` or ``push``; ``ratio`` is the scale after over
    before; ``camera`` is False for a group that is not a location, angle, shot or setup (a gag that grows)."""

    kind: str
    group: str
    start: float
    end: float
    ratio: float
    camera: bool


@dataclass(frozen=True)
class Pause:
    """A silence between two spoken lines, and the rendered sound's mean level inside it (``None``: unmeasured)."""

    start: float
    end: float
    level_db: float | None

    @property
    def quiet(self) -> bool | None:
        return None if self.level_db is None else self.level_db <= QUIET_DB


@dataclass(frozen=True)
class Flash:
    """A stretch of a render in which ``share`` of the picture, at its worst, flashes more than the limit allows."""

    start: float
    end: float
    share: float


@dataclass(frozen=True)
class Hold:
    """A stretch of a render in which the picture stands: every frame is still the first one."""

    start: float
    end: float


@dataclass(frozen=True)
class Craft:
    slug: str
    moves: list[Move]
    pauses: list[Pause]
    opening: list[tuple[float, float]]
    flashes: list[Flash] = field(default_factory=list)
    holds: list[Hold] = field(default_factory=list)
    clipped: list[tuple[str, float]] = field(default_factory=list)
    crowded: list[tuple[float, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "slug": self.slug,
            "moves": [asdict(m) for m in self.moves],
            "pauses": [
                {
                    "start": p.start,
                    "end": p.end,
                    "level_db": None if p.level_db is None else max(p.level_db, FLOOR_DB),
                    "quiet": p.quiet,
                }
                for p in self.pauses
            ],
            "opening": [{"start": a, "end": b} for a, b in self.opening],
            "flashes": [asdict(f) for f in self.flashes],
            "holds": [asdict(h) for h in self.holds],
            "clipped": [{"line": line, "lost": lost} for line, lost in self.clipped],
            "crowded": [{"start": at, "gap": gap} for at, gap in self.crowded],
        }


def moves(document: bytes) -> list[Move]:
    """Every change of framing in the scene ``document``, in time order; the signature marks never count."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError as e:
        raise CraftError(f"the scene is not XML: {e}") from None
    found = []
    shifts = _sequence_shifts(root)
    for group in root.iter("group"):
        gid = group.get("id") or ""
        if gid.startswith("sig-"):
            continue
        scale = {a.get("property"): a for a in group.findall("animate")}
        if "scaleX" not in scale or "scaleY" not in scale:
            continue
        keys = [(float(k.get("time", "nan")), float(k.get("value", "nan"))) for k in scale["scaleX"].iter("key")]
        tall = {float(k.get("time", "nan")): float(k.get("value", "nan")) for k in scale["scaleY"].iter("key")}
        hold = scale["scaleX"].get("defaultInterpolation") == "hold"
        for (t0, v0), (t1, v1) in zip(keys, keys[1:], strict=False):
            if not v0 or abs(v1 / v0 - 1) < MIN_RATIO or tall.get(t0) != v0 or tall.get(t1) != v1:
                continue
            cut = hold or t1 - t0 < CUT
            kind = "punch-in" if cut else ("crash" if t1 - t0 <= SNAP + 1e-9 else "push")
            start, shift = (t1 if cut else t0), shifts.get(group, 0.0)
            found.append(
                Move(kind, gid, round(start + shift, 3), round(t1 + shift, 3), round(v1 / v0, 2),
                     bool(CAMERA.fullmatch(gid)))
            )  # fmt: skip
    return sorted(found, key=lambda m: (m.start, m.group))


def doubled_captions(document: bytes) -> list[str]:
    """Each pair of captions that share a band at once, by name: for a few frames both lines print over each other,
    and a caption gate that reads pixels at a line's middle never sees it."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError as e:
        raise CraftError(f"not a scene document: {e}") from None
    layers = [
        (_seconds(n, "start"), _seconds(n, "end"), n.get("y"), n.get("id", ""))
        for n in root.iter()
        if n.tag.rpartition("}")[2] == "layer" and n.get("id", "").endswith("-caption") and n.get("start")
    ]
    bands: dict[str | None, list[tuple[float, float, str]]] = {}
    for start, end, band, name in sorted(layers, key=lambda layer: (layer[0], layer[1])):
        bands.setdefault(band, []).append((start, end, name))
    return [
        f"{a[2]} and {b[2]} share the band for {a[1] - b[0]:.2f} s"
        for held in bands.values()
        for a, b in zip(held, held[1:], strict=False)
        if a[1] > b[0] + DOUBLED
    ]


def _sequence_shifts(root: ET.Element) -> dict[ET.Element, float]:
    """How far each element's clock is moved by the ``<sequence>`` elements above it, as the engine places them: a
    child plays where the one before it ended (``end``), plus the sequence's ``timeGap``, its contents moved with it.
    A child with a ``startMarker`` is placed by the engine on its marker, which craft does not resolve, so it and what
    follows it keep the sequence's clock, as do the children after one without an ``end``."""
    shifts: dict[ET.Element, float] = {}

    def walk(node: ET.Element, shift: float) -> None:
        if node.tag != "sequence":
            for child in node:
                shifts[child] = shift
                walk(child, shift)
            return
        cursor: float | None = shift + _seconds(node, "start")
        gap = _seconds(node, "timeGap")
        for child in node:
            if child.tag == "transition":
                continue
            marked = child.get("startMarker") is not None
            moved = shift if cursor is None or marked else cursor
            shifts[child] = moved
            walk(child, moved)
            placed = cursor is not None and not marked and child.get("end") is not None
            cursor = moved + _seconds(child, "end") + gap if placed else None

    walk(root, 0.0)
    return shifts


def _seconds(node: ET.Element, name: str) -> float:
    value = node.get(name)
    try:
        return 0.0 if value is None else float(value)
    except ValueError:
        raise CraftError(f"<{node.tag} id={node.get('id')!r}> {name}={value!r} is not a number of seconds") from None


def _number(value, where: str) -> float:
    if not checks.number(value):
        raise CraftError(f"{where} must be a number, got {value!r}")
    return float(value)


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise CraftError(f"{path}: {e}") from None
    if not isinstance(data, dict):
        raise CraftError(f"{path}: not a JSON object")
    return data


def lines(project: Path) -> list[tuple[float, float]]:
    """The spoken lines of ``project`` as ``(start, end)`` seconds, in order: from ``dialogue.json`` phrases, the
    ``line`` items of ``narration.json``, or the spoken takes of a :mod:`srstudio.takes` ``timeline.json`` (each take's
    speech, without the hold after it; effect takes are skipped); an empty list for a project with none (a silent
    episode)."""
    project = Path(project)
    spans = []
    if (project / "dialogue.json").is_file():
        rows = _read(project / "dialogue.json").get("phrases")
        if not isinstance(rows, list):
            raise CraftError(f"{project}/dialogue.json: phrases must be a list")
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise CraftError(f"{project}/dialogue.json: phrase {i} is not an object")
            spans.append((_number(row.get("start"), f"phrase {i} start"), _number(row.get("end"), f"phrase {i} end")))
    elif (project / "narration.json").is_file():
        rows = _read(project / "narration.json").get("items")
        if not isinstance(rows, list):
            raise CraftError(f"{project}/narration.json: items must be a list")
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise CraftError(f"{project}/narration.json: item {i} is not an object")
            if row.get("phase") != "line":
                continue
            start = _number(row.get("start"), f"item {i} start")
            spans.append((start, start + _number(row.get("speech_duration"), f"item {i} speech_duration")))
    elif (project / "timeline.json").is_file():
        rows = _read(project / "timeline.json").get("items")
        if not isinstance(rows, list):
            raise CraftError(f"{project}/timeline.json: items must be a list")
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise CraftError(f"{project}/timeline.json: take {i} is not an object")
            start = _number(row.get("start"), f"take {i} start")
            speech = _number(row.get("speech_duration"), f"take {i} speech_duration")
            if speech:  # an effect take has no speech
                spans.append((start, start + speech))
    for start, end in spans:
        if end < start:
            raise CraftError(f"{project}: a line ends ({end}) before it starts ({start})")
    return sorted(spans)


def clipped(project: Path) -> list[tuple[str, float]]:
    """The spoken lines of ``project`` a recording cut short because the next line starts too soon, as ``(line id,
    seconds of speech lost)``. A clipped punchline sounds like a bad take and passes every other check, so it is named
    here. Empty for an episode without a ``narration.json``; an item that cannot be read raises :class:`CraftError`."""
    path = Path(project) / "narration.json"
    if not path.is_file():
        return []
    rows = _read(path).get("items")
    if not isinstance(rows, list):
        raise CraftError(f"{path}: items must be a list")
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CraftError(f"{path}: item {i} is not an object")
        if row.get("phase") != "line":
            continue
        line, cut = row.get("id"), row.get("cut")
        if not isinstance(line, str) or not isinstance(cut, bool):
            raise CraftError(f"{path}: item {i} needs a text id and a true or false cut")
        speech = _number(row.get("speech_duration"), f"item {i} speech_duration")
        kept = _number(row.get("duration"), f"item {i} duration")
        if cut and speech > kept:
            out.append((line, round(speech - kept, 3)))
    return out


@dataclass(frozen=True)
class Statement:
    """The words a reel opens on, as recorded, and when in the master the last of them stops."""

    text: str
    end: float


def statement(project: Path, lines: Sequence[str]) -> Statement:
    """The statement made of ``lines``, the line ids a pilot names (``FIRST_STATEMENT``), read from the takes the master
    was built from (``voiced/speech.json``). It ends where the last letter of the last named line ends: closing
    punctuation has no sound of its own. Raises :class:`CraftError` for no lines, an unknown id or a take with no
    letters, so a missing measure is never a pass."""
    path = Path(project) / "voiced" / "speech.json"
    takes = _read(path).get("takes")
    if not isinstance(takes, list):
        raise CraftError(f"{path}: takes must be a list")
    if not lines:
        raise CraftError(f"{path}: a statement needs at least one line")
    named = {take.get("id"): take for take in takes if isinstance(take, dict)}
    texts, end = [], 0.0
    for line in lines:
        take = named.get(line)
        if take is None:
            raise CraftError(f"{path}: no take {line!r}")
        characters, ends = take.get("characters"), take.get("ends")
        if not (isinstance(characters, list) and isinstance(ends, list) and len(characters) == len(ends)):
            raise CraftError(f"{path}: take {line} needs a time for every letter")
        spoken = [i for i, c in enumerate(characters) if isinstance(c, str) and c.isalnum()]
        if not spoken:
            raise CraftError(f"{path}: take {line} has no letters")
        texts.append("".join(str(c) for c in characters))
        end = _number(take.get("at"), f"take {line} at") + _number(ends[spoken[-1]], f"take {line} end")
    return Statement(" ".join(texts), round(end, 3))


def pauses(spoken: Sequence[tuple[float, float]], threshold: float = PAUSE) -> list[tuple[float, float]]:
    """The gaps of at least ``threshold`` seconds in which no line of ``spoken`` plays."""
    if not (checks.number(threshold) and threshold > 0):
        raise CraftError(f"threshold {threshold} must be > 0")
    gaps: list[tuple[float, float]] = []
    heard_until: float | None = None
    for start, end in sorted(spoken):
        if heard_until is not None and start - heard_until >= threshold:
            gaps.append((heard_until, start))
        heard_until = end if heard_until is None else max(heard_until, end)
    return gaps


def crowded(spoken: Sequence[tuple[float, float]], least: float = BREATH) -> list[tuple[float, float]]:
    """``(start, gap)`` of each line that starts less than ``least`` seconds after the line before ended: two voices
    with no room between them. A line that talks over the last one has a gap below zero. Written that way it can be the
    joke, so this says where to listen, and the report keeps it out of the verdict."""
    return [
        (round(after[0], 3), round(after[0] - before[1], 3))
        for before, after in zip(spoken, spoken[1:], strict=False)
        if after[0] - before[1] < least
    ]


def opening_silences(
    spoken: Sequence[tuple[float, float]], *, within: float = OPENING, limit: float = OPENING_LIMIT
) -> list[tuple[float, float]]:
    """The stretches of at least ``limit`` seconds with no line in the first ``within`` seconds: gaps between lines,
    and the wait before the first line and after the last. A sound effect or a gag can fill one, so read the picture."""
    if not (checks.number(within) and within > 0 and checks.number(limit) and limit > 0):
        raise CraftError(f"an opening of {within} s with a limit of {limit} s is not one")
    gaps: list[tuple[float, float]] = []
    heard_until = 0.0
    for start, end in sorted(spoken):
        if min(start, within) - heard_until >= limit:
            gaps.append((heard_until, min(start, within)))
        heard_until = max(heard_until, end)
    if within - heard_until >= limit:
        gaps.append((heard_until, within))
    return gaps


def levels(
    video: Path,
    spans: Sequence[tuple[float, float]],
    *,
    ffmpeg: str = "ffmpeg",
    run: Callable[..., subprocess.CompletedProcess] | None = None,
) -> list[float]:
    """The mean level (dB, ``-inf`` for digital silence) of the sound of ``video`` inside each span, by ffmpeg's
    ``volumedetect``. Raises :class:`CraftError` when ffmpeg fails or reports no level."""
    run = run or _run
    out = []
    for start, end in spans:
        cmd = [ffmpeg, "-hide_banner", "-nostats", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(video)]
        cmd += ["-vn", "-af", "volumedetect", "-f", "null", "-"]
        try:
            done = run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError as e:
            raise CraftError(f"ffmpeg was not found at {ffmpeg!r}") from e
        if done.returncode != 0:
            reason = (done.stderr or "").strip().splitlines()[-1:] or ["no output"]
            raise CraftError(f"ffmpeg failed on {video} at {start:.2f} s: {reason[0]}")
        m = _MEAN.search(done.stderr or "")
        if not m:
            raise CraftError(f"ffmpeg reported no mean_volume for {video} at {start:.2f} s")
        out.append(-math.inf if m.group(1) == "-inf" else float(m.group(1)))
    return out


def luminance(
    video: Path, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe", run: Callable[..., Any] | None = None
) -> tuple[np.ndarray, float]:
    """Every frame of ``video``, small, as linear relative luminance (frames × height × width, 0 to 1), and its fps.
    Raises :class:`CraftError` when the video cannot be read."""
    run = run or _run
    probe = [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate"]
    probe += ["-of", "csv=p=0", str(video)]
    read = [ffmpeg, "-v", "error", "-i", str(video), "-vf", f"scale={SCAN_WIDTH}:{SCAN_HEIGHT},format=gray"]
    read += ["-f", "rawvideo", "-"]
    try:
        rate = run(probe, capture_output=True, text=True, check=False)
        raw = run(read, capture_output=True, check=False)
    except FileNotFoundError as e:
        raise CraftError(f"ffmpeg or ffprobe was not found: {e}") from e
    if rate.returncode != 0 or raw.returncode != 0 or not raw.stdout:
        raise CraftError(f"ffmpeg could not read {video}")
    top, _, bottom = rate.stdout.strip().partition("/")
    fps = float(top) / float(bottom or 1)
    picture = np.frombuffer(raw.stdout, np.uint8).reshape(-1, SCAN_HEIGHT, SCAN_WIDTH) / 255.0
    return np.where(picture <= 0.04045, picture / 12.92, ((picture + 0.055) / 1.055) ** 2.4), fps


def _swings(frames: np.ndarray) -> np.ndarray:
    """Per frame and pixel, whether a swing in the opposite direction to the last one has just completed. The level a
    pixel swings from follows it as it keeps going the same way, so a long slow change is one swing, not many."""
    swings = np.zeros(frames.shape, bool)
    level, going = frames[0].copy(), np.zeros(frames.shape[1:])
    for i in range(1, len(frames)):
        now = frames[i]
        up = now - level >= SWING
        down = (level - now >= SWING) & (np.minimum(now, level) < BRIGHT)
        swings[i] = (up & (going <= 0)) | (down & (going >= 0))
        going = np.where(up, 1.0, np.where(down, -1.0, going))
        further = np.where(going > 0, np.maximum(level, now), np.where(going < 0, np.minimum(level, now), level))
        level = np.where(up | down, now, further)
    return swings


def flashing(frames: np.ndarray, fps: float, share: float = FLASH_SHARE) -> list[Flash]:
    """The stretches of ``frames`` (see :func:`luminance`) in which at least ``share`` of the picture flashes more than
    :data:`FLASHES_A_SECOND` times within a second. The whole picture is the measure here, not the guideline's field of
    view, so the numbers are a map of where to look: a render can list a stretch and pass the strict encode."""
    if len(frames) == 0:
        raise CraftError("a picture with no frames cannot be scanned")
    second = max(1, round(fps))
    running = _swings(frames).cumsum(axis=0)
    over = [
        (i, float((running[i] - running[max(0, i - second)] > 2 * FLASHES_A_SECOND).mean()))
        for i in range(1, len(frames))
    ]
    out: list[Flash] = []
    stretch: list[tuple[int, float]] = []
    for i, part in [*over, (len(frames), 0.0)]:
        if part >= share:
            stretch.append((i, part))
        elif stretch:
            begins = max(0.0, stretch[0][0] / fps - 1.0)
            out.append(Flash(round(begins, 3), round(stretch[-1][0] / fps, 3), round(max(p for _, p in stretch), 3)))
            stretch = []
    return out


def holding(frames: np.ndarray, fps: float) -> list[Hold]:
    """The stretches of ``frames`` (see :func:`luminance`) of at least :data:`HOLD_LEAST` seconds in which the picture
    stands. Each frame is compared with the first of the stretch and not with the one before: a slow change adds up
    against it, and a keyframe, which repaints every pixel a little, does not read as motion."""
    if len(frames) == 0:
        raise CraftError("a picture with no frames cannot be scanned")
    out: list[Hold] = []
    start = 0
    for i in range(1, len(frames) + 1):
        if i == len(frames) or (np.abs(frames[i] - frames[start]) > HOLD_CHANGE).mean() > HOLD_SHARE:
            if (i - start) / fps >= HOLD_LEAST:
                out.append(Hold(round(start / fps, 3), round(i / fps, 3)))
            start = i
    return out


def measure(
    project: Path,
    *,
    video: Path | None = None,
    threshold: float = PAUSE,
    levels: Callable[[Path, Sequence[tuple[float, float]]], Sequence[float]] = levels,
) -> Craft:
    """The craft report of the episode project ``project`` (``<slug>.scene.xml`` inside it); with ``video`` (its
    render) each pause carries the measured level, and the stretches that flash or stand still are listed."""
    project = Path(project)
    scene = project / f"{project.name}.scene.xml"
    if not scene.is_file():
        raise CraftError(f"{project} has no scene {scene.name}")
    spoken = lines(project)
    gaps = pauses(spoken, threshold)
    measured: Sequence[float | None] = [None] * len(gaps)
    flashes: list[Flash] = []
    holds: list[Hold] = []
    if video is not None:
        measured = list(levels(Path(video), gaps))
        if len(measured) != len(gaps):
            raise CraftError(f"{len(measured)} levels for {len(gaps)} pauses")
        frames, fps = luminance(Path(video))
        flashes, holds = flashing(frames, fps), holding(frames, fps)
    return Craft(
        project.name,
        moves(scene.read_bytes()),
        list(Pause(round(a, 3), round(b, 3), level) for (a, b), level in zip(gaps, measured, strict=True)),
        [(round(a, 3), round(b, 3)) for a, b in opening_silences(spoken)],
        flashes,
        holds,
        clipped(project),
        crowded(spoken),
    )
