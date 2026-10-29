"""Comic craft, measured: the camera moves an episode makes and the pauses between its spoken lines.

Where the camera is and when nobody speaks are part of a joke (crash zooms, punch-ins on the cut, slow pushes,
the awkward pause). :func:`moves` reads them from the scene: every uniform scale change (``scaleX`` and ``scaleY``
alike, so a spin or a stretch is not a zoom) of at least 15 % on a group, told apart by speed (a hold key or a step
under :data:`CUT` is a punch-in on the cut, :data:`~srstudio.camera.SNAP` or faster is a crash zoom, slower a push)
and marked as the camera when the group is a location, an angle, a shot or a setup.
:func:`pauses` finds the silences between the lines of ``dialogue.json``, ``narration.json`` or a takes
``timeline.json``, and :func:`levels` measures the rendered sound inside each one, so a pause meant to be awkward is
shown to be quiet, or filled.
``srstudio craft`` prints the report (schema :data:`SCHEMA`).
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .camera import SNAP
from .errors import SrstudioError

__all__ = [
    "SCHEMA",
    "CUT",
    "MIN_RATIO",
    "PAUSE",
    "QUIET_DB",
    "CraftError",
    "Move",
    "Pause",
    "Craft",
    "moves",
    "lines",
    "pauses",
    "levels",
    "measure",
]

SCHEMA = "1.0.0"
CUT = 1 / 60  # a step faster than half a frame at 30 fps is a cut, not a move
MIN_RATIO = 0.15  # a scale change smaller than this is a breath or a squash, not a move
PAUSE = 0.8  # seconds between lines that count as a pause
QUIET_DB = -35.0  # mean level at or under which a pause is quiet: no music or effect fills it
FLOOR_DB = -120.0  # how digital silence (-inf) is written in the JSON report
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
class Craft:
    slug: str
    moves: list[Move]
    pauses: list[Pause]

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
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
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


def pauses(spoken: Sequence[tuple[float, float]], threshold: float = PAUSE) -> list[tuple[float, float]]:
    """The gaps of at least ``threshold`` seconds in which no line of ``spoken`` plays."""
    if not (math.isfinite(threshold) and threshold > 0):
        raise ValueError(f"threshold {threshold} must be > 0")
    gaps: list[tuple[float, float]] = []
    heard_until: float | None = None
    for start, end in sorted(spoken):
        if heard_until is not None and start - heard_until >= threshold:
            gaps.append((heard_until, start))
        heard_until = end if heard_until is None else max(heard_until, end)
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


def measure(
    project: Path,
    *,
    video: Path | None = None,
    threshold: float = PAUSE,
    levels: Callable[[Path, Sequence[tuple[float, float]]], Sequence[float]] = levels,
) -> Craft:
    """The craft report of the episode project ``project`` (``<slug>.scene.xml`` inside it); with ``video`` (its
    render) each pause carries the measured level."""
    project = Path(project)
    scene = project / f"{project.name}.scene.xml"
    if not scene.is_file():
        raise CraftError(f"{project} has no scene {scene.name}")
    gaps = pauses(lines(project), threshold)
    measured: Sequence[float | None] = [None] * len(gaps)
    if video is not None:
        measured = list(levels(Path(video), gaps))
        if len(measured) != len(gaps):
            raise CraftError(f"{len(measured)} levels for {len(gaps)} pauses")
    return Craft(
        project.name,
        moves(scene.read_bytes()),
        list(Pause(round(a, 3), round(b, 3), level) for (a, b), level in zip(gaps, measured, strict=True)),
    )
