"""The engine's ``--strict`` findings at first delivery, and the records that clear a false one (ADR 0078).

``scene-render encode --strict`` exits non-zero on a finding and writes the master all the same, and delivery never
read the result, so a reel with findings could ship. This gate reads each new reel's ``qa/render-report.json`` beside
the frame gates (ADR 0073). A reel in the manifest is published and frozen, and it never comes here.

The rule is the publishing side's: "A reel whose findings are all proven false ships. A finding counts as proven false
only when it's measured on the rendered frames, not argued", "signed off by a reviewer who isn't the author", and "Real
findings still get fixed." So a finding is cleared by a :class:`Record` in ``episodes/strict/<slug>.json`` and by
nothing else, and only ``LEG-SHORT``, ``LEG-CONTRAST`` and ``TXT-FIT`` can be cleared. The rule says how to measure the
first two. The third is the proof the publishing side accepted on ``ill-get-this``: the card "touches the edge only
while it's thrown in", and at rest the text is "fully inside it".

A record is written by agents, so it is model output, and this is the verification CLAUDE.md requires of it: a typed
parse that refuses unknown fields (:func:`parse_record`), semantic checks that the numbers agree with each other and
beat the minimum, a typed refusal that names the reel, failing-input tests in ``tests/test_strict_gate.py``, and no
loop for a model to steer. No model is called here. :func:`strict_defects` then holds the record to the files: the
report's own minimum, the master's hash and frame rate, and each cited frame decoded from the master itself.

The gate certifies the numbers against the files and no more. It cannot see that the text is legible in the frames it
is shown, or that the text stayed up between two cited frames. Those are the reviewer's, and it cannot see who the
reviewer was: that they are not the author is a rule of the process.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .cast_card import contrast
from .frame_gates import _duration
from .releases import SLUG, Release
from .social import DeliveryError, Drift

__all__ = [
    "CONTRAST",
    "ENGINE_REPORT",
    "FIT",
    "FORMAT",
    "RECORD_VERSION",
    "SHORT",
    "Cleared",
    "Contrast",
    "Evidence",
    "Finding",
    "Fit",
    "OnScreen",
    "Record",
    "Report",
    "StrictError",
    "listing",
    "parse_record",
    "read_all",
    "read_record",
    "read_report",
    "strict_defects",
]

FORMAT = "scene-render-report/1"  # the engine's report, SREP 18
RECORD_VERSION = "1.0.0"
ENGINE_REPORT = "qa/render-report.json"  # in a project, as the reel styles declare it on their output
SHORT = "LEG-SHORT"
CONTRAST = "LEG-CONTRAST"
FIT = "TXT-FIT"
NOT_COUNTED = "info"  # what --strict leaves out; any other severity counts, a new one included
_HASH = re.compile(r"[0-9a-f]{64}")
_COLOUR = re.compile(r"#[0-9a-f]{6}")
_SECONDS_SLACK = 0.001  # a record's rounding of frames over fps
_RATIO_SLACK = 0.05  # a median's rounding to whole #rrggbb channels
_SAME = 1e-3  # seconds, and the frame rate: a report's or a stream's number, read back


class StrictError(DeliveryError):
    """A report or a record that cannot be read or does not hold. It refuses its own reel, and nobody else's."""


@dataclass(frozen=True)
class Finding:
    """One finding of the report that ``--strict`` counts."""

    code: str
    severity: str
    node: str  # the element's id, or its path when it has none
    start: float | None
    end: float | None
    measured: float | None
    limit: float | None
    unit: str

    @property
    def key(self) -> tuple[str, str, str]:
        """What a record names it by: a report gives a finding no id, and one track can repeat a code."""
        return self.code, self.node, "" if self.start is None else f"{self.start:.3f}"

    def __str__(self) -> str:
        at = "" if self.start is None else f" at {self.start:.3f}"
        said = "" if self.measured is None or self.limit is None else f" measured {self.measured:g} of {self.limit:g}"
        return f"--strict {self.severity}: {self.code} {self.node}{at}{said}{f' {self.unit}' if said else ''}"


@dataclass(frozen=True)
class Report:
    """What a reel's report says, for the output it was written for."""

    scene_sha256: str
    start: float
    end: float
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class OnScreen:
    """The real time on screen of a text, first to last legible frame, against the rule's minimum in seconds."""

    first_frame: int
    last_frame: int
    seconds: float
    minimum: float

    @property
    def cites(self) -> tuple[int, ...]:
        return self.first_frame, self.last_frame

    def __str__(self) -> str:
        span = f"frames {self.first_frame} to {self.last_frame}"
        return f"on screen {self.seconds:.3f} s, {span}, minimum {self.minimum:g} s"


@dataclass(frozen=True)
class Contrast:
    """The contrast of a text on the composited frame, at its worst frame, against the rule's minimum ratio."""

    first_frame: int
    last_frame: int
    lowest_frame: int
    fill: str
    back: str
    ratio: float
    minimum: float

    @property
    def cites(self) -> tuple[int, ...]:
        return (self.lowest_frame,)

    def __str__(self) -> str:
        worst = f"lowest {self.ratio:.2f}:1 at frame {self.lowest_frame}"
        return f"{worst}, {self.fill} on {self.back}, minimum {self.minimum:g}:1"


@dataclass(frozen=True)
class Fit:
    """A text cut only while it comes in: at rest, its box of glyphs inside the box that holds it and inside the frame.

    Boxes are left, top, right and bottom, in pixels of the frame, and each edge is a pixel of the box."""

    first_frame: int  # the first frame the box is on screen
    rest_frame: int  # the first frame it stays still
    last_frame: int
    text: tuple[int, int, int, int]
    box: tuple[int, int, int, int]
    limit: float

    @property
    def cites(self) -> tuple[int, ...]:
        return self.first_frame, self.rest_frame, self.last_frame

    @property
    def minimum(self) -> float:
        return self.limit

    @property
    def past(self) -> int:
        """How far the text reaches past its box at rest, in pixels."""
        left, top, right, bottom = self.text
        edge_left, edge_top, edge_right, edge_bottom = self.box
        return max(0, edge_left - left, edge_top - top, right - edge_right, bottom - edge_bottom)

    def __str__(self) -> str:
        rest = f"inside its box from frame {self.rest_frame} to frame {self.last_frame}"
        return f"{rest}, {self.past} px past it, limit {self.limit:g} px, thrown in from frame {self.first_frame}"


@dataclass(frozen=True)
class Evidence:
    """A frame of the master as a picture, at ``path`` inside the reel's project."""

    frame: int
    path: str


@dataclass(frozen=True)
class Cleared:
    """One finding proven false: which, what the frames measured, and the frames."""

    code: str
    node: str
    at: float
    measurement: OnScreen | Contrast | Fit
    frames: tuple[Evidence, ...]

    @property
    def key(self) -> tuple[str, str, str]:
        return self.code, self.node, f"{self.at:.3f}"

    def __str__(self) -> str:
        return f"{self.code} {self.node}"

    @property
    def named(self) -> str:
        return f"{self} at {self.at:.3f}"


@dataclass(frozen=True)
class Record:
    """Everything a reel's author proved false, measured on one master of one scene, and who signed it off."""

    schema_version: str
    slug: str
    scene_sha256: str
    video_sha256: str
    fps: float
    author: str
    reviewer: str
    cleared: tuple[Cleared, ...]


# -- reading -------------------------------------------------------------------------------------------------------
def _object(raw: object, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StrictError(f"{where} is not an object")
    return raw


def _fields(raw: object, where: str, names: Sequence[str]) -> dict[str, Any]:
    """``raw`` as an object of exactly the fields ``names``."""
    found = _object(raw, where)
    for name in sorted(set(found) - set(names)):
        raise StrictError(f"{where}: unknown field {name}")
    for name in names:
        if name not in found:
            raise StrictError(f"{where}: missing field {name}")
    return found


def _number(raw: object, name: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float) or not math.isfinite(raw):
        raise StrictError(f"{name} {raw!r} is not a number")
    return float(raw)


def _positive(raw: object, name: str) -> float:
    value = _number(raw, name)
    if value <= 0:
        raise StrictError(f"{name} {value:g} is not above zero")
    return value


def _frame(raw: object, name: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise StrictError(f"{name} {raw!r} is not a frame number")
    return raw


def _text(raw: object, name: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise StrictError(f"{name} {raw!r} is empty")
    return raw


def _matching(raw: object, pattern: re.Pattern[str], name: str) -> str:
    if not isinstance(raw, str) or not pattern.fullmatch(raw):
        raise StrictError(f"{name} {raw!r} is malformed")
    return raw


def _on_screen(raw: object, where: str, fps: float) -> OnScreen:
    found = _fields(raw, where, ("first_frame", "last_frame", "seconds", "minimum"))
    first, last = _frame(found["first_frame"], "first_frame"), _frame(found["last_frame"], "last_frame")
    seconds, minimum = _number(found["seconds"], "seconds"), _positive(found["minimum"], "minimum")
    if first > last:
        raise StrictError(f"{where}: first frame {first} is after the last {last}")
    count = last - first + 1
    if abs(seconds - count / fps) > _SECONDS_SLACK:
        raise StrictError(f"{where}: {count} frames at {fps:g} fps are {count / fps:.3f} s, not {seconds:.3f} s")
    if seconds < minimum:  # the engine's test: equal to the minimum is not a finding
        raise StrictError(f"{where}: {seconds:.3f} s does not reach the minimum of {minimum:g}")
    return OnScreen(first, last, seconds, minimum)


def _contrast(raw: object, where: str, fps: float) -> Contrast:
    names = ("first_frame", "last_frame", "lowest_frame", "fill", "back", "ratio", "minimum")
    found = _fields(raw, where, names)
    first, last = _frame(found["first_frame"], "first_frame"), _frame(found["last_frame"], "last_frame")
    lowest = _frame(found["lowest_frame"], "lowest_frame")
    fill, back = _matching(found["fill"], _COLOUR, "fill"), _matching(found["back"], _COLOUR, "back")
    ratio, minimum = _number(found["ratio"], "ratio"), _positive(found["minimum"], "minimum")
    if not first <= lowest <= last:
        raise StrictError(f"{where}: worst frame {lowest} is outside {first} to {last}")
    if abs(contrast(fill, back) - ratio) > _RATIO_SLACK:
        raise StrictError(f"{where}: {fill} on {back} is {contrast(fill, back):.2f}:1, not {ratio:.2f}:1")
    if ratio < minimum:
        raise StrictError(f"{where}: {ratio:.2f}:1 does not reach the minimum of {minimum:g}")
    return Contrast(first, last, lowest, fill, back, ratio, minimum)


def _box(raw: object, name: str) -> tuple[int, int, int, int]:
    if not isinstance(raw, list) or len(raw) != 4:
        raise StrictError(f"{name} {raw!r} is not a left, top, right and bottom")
    left, top, right, bottom = (_frame(edge, name) for edge in raw)
    if left >= right or top >= bottom:
        raise StrictError(f"{name} {raw!r} has no area")
    return left, top, right, bottom


def _fit(raw: object, where: str, _fps: float) -> Fit:
    found = _fields(raw, where, ("first_frame", "rest_frame", "last_frame", "text", "box", "limit"))
    first, last = _frame(found["first_frame"], "first_frame"), _frame(found["last_frame"], "last_frame")
    rest = _frame(found["rest_frame"], "rest_frame")
    limit = _number(found["limit"], "limit")
    if limit < 0:
        raise StrictError(f"{where}: limit {limit:g} is below zero")
    if not first <= rest <= last:
        raise StrictError(f"{where}: rest frame {rest} is outside {first} to {last}")
    fit = Fit(first, rest, last, _box(found["text"], "text"), _box(found["box"], "box"), limit)
    if fit.past > limit:
        raise StrictError(f"{where}: the text is {fit.past} px past its box at rest, limit {limit:g} px")
    return fit


_MEASURES: dict[str, Callable[[object, str, float], OnScreen | Contrast | Fit]] = {
    SHORT: _on_screen,
    CONTRAST: _contrast,
    FIT: _fit,
}


def _evidence(raw: object, where: str) -> Evidence:
    found = _fields(raw, where, ("frame", "path"))
    path = _text(found["path"], "path")
    if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
        raise StrictError(f"{where}: {path} is not inside the project")
    return Evidence(_frame(found["frame"], "frame"), path)


def _cleared(raw: object, where: str, fps: float) -> Cleared:
    found = _fields(raw, where, ("code", "node", "at", "measurement", "frames"))
    code = _text(found["code"], "code")
    if code not in _MEASURES:
        raise StrictError(f"{where}: {code} is not a finding frames can prove false")
    at = _number(found["at"], "at")
    measurement = _MEASURES[code](found["measurement"], f"{where}: {code}", fps)
    if not isinstance(found["frames"], list) or not found["frames"]:
        raise StrictError(f"{where}: cites no frame")
    frames = tuple(_evidence(f, f"{where}: frames[{i}]") for i, f in enumerate(found["frames"]))
    cited = {f.frame for f in frames}
    for number in measurement.cites:
        if number not in cited:
            raise StrictError(f"{where}: does not cite frame {number}")
    return Cleared(code, _text(found["node"], "node"), at, measurement, frames)


def parse_record(raw: object) -> Record:
    """``raw``, a loaded record, as a :class:`Record`, or :class:`StrictError` for anything that proves nothing."""
    names = ("schema_version", "slug", "scene_sha256", "video_sha256", "fps", "author", "reviewer", "cleared")
    found = _fields(raw, "the record", names)
    if found["schema_version"] != RECORD_VERSION:
        raise StrictError(f"record version {found['schema_version']!r} is not {RECORD_VERSION}")
    slug = _matching(found["slug"], SLUG, "slug")
    fps = _positive(found["fps"], "fps")
    author, reviewer = _text(found["author"], "author"), _text(found["reviewer"], "reviewer")
    if author.strip().casefold() == reviewer.strip().casefold():
        raise StrictError(f"the reviewer is the author: {author}")
    if not isinstance(found["cleared"], list) or not found["cleared"]:
        raise StrictError("the record clears nothing")
    cleared = tuple(_cleared(c, f"cleared[{i}]", fps) for i, c in enumerate(found["cleared"]))
    seen: set[tuple[str, str, str]] = set()
    for entry in cleared:
        if entry.key in seen:
            raise StrictError(f"the record clears {entry.named} twice")
        seen.add(entry.key)
    scene = _matching(found["scene_sha256"], _HASH, "scene_sha256")
    video = _matching(found["video_sha256"], _HASH, "video_sha256")
    return Record(RECORD_VERSION, slug, scene, video, fps, author, reviewer, cleared)


def _load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise StrictError(f"{path.name}: cannot be read: {e}") from e
    except ValueError as e:
        raise StrictError(f"{path.name}: not JSON: {e}") from e


def read_record(path: Path) -> Record:
    """The record at ``path``, which must be the one its name says."""
    raw = _load(path)
    try:
        record = parse_record(raw)
    except StrictError as e:
        raise StrictError(f"{path.name}: {e}") from e
    if record.slug != path.stem:
        raise StrictError(f"{path.name} is the record of {record.slug}")
    return record


def read_all(folder: Path, releases: Mapping[str, Release]) -> list[Record]:
    """Every record in ``folder``. One that is malformed, or that names no release, raises :class:`StrictError`."""
    records = [read_record(path) for path in sorted(Path(folder).glob("*.json"))]
    for record in records:
        if record.slug not in releases:
            raise StrictError(f"{record.slug}.json: no release of that name")
    return records


def _time(raw: object) -> tuple[float | None, float | None]:
    return (None, None) if not isinstance(raw, list) or len(raw) != 2 else (_number(raw[0], "t"), _number(raw[1], "t"))


def _finding(raw: object) -> Finding:
    found = _object(raw, "a finding")
    start, end = _time(found.get("time"))
    measured, limit = found.get("measured"), found.get("limit")
    return Finding(
        _text(found.get("code"), "a finding's code"),
        _text(found.get("severity"), "a finding's severity"),
        _text(found.get("node") or found.get("path"), "a finding's node"),
        start,
        end,
        None if measured is None else _number(measured, "measured"),
        None if limit is None else _number(limit, "limit"),
        str(found.get("unit") or ""),
    )


def read_report(path: Path) -> Report:
    """The findings ``--strict`` counts in the report at ``path``. The report is the engine's to extend, so unknown
    fields are its own; a report that cannot say what it found raises :class:`StrictError`."""
    found = _object(_load(path), f"{path.name}")
    if found.get("format") != FORMAT:
        raise StrictError(f"{path.name}: format {found.get('format')!r} is not {FORMAT}")
    if not isinstance(found.get("findings"), list):
        raise StrictError(f"{path.name}: no findings list")
    scene, output = _object(found.get("scene"), "its scene"), _object(found.get("output"), "its output")
    findings = (_finding(f) for f in found["findings"])
    counted = tuple(f for f in findings if f.severity != NOT_COUNTED)
    window = _number(output.get("start"), "start"), _number(output.get("end"), "end")
    return Report(_text(scene.get("sha256"), "its scene's hash"), *window, counted)


# -- the master ----------------------------------------------------------------------------------------------------
def _stream(video: Path) -> tuple[int, int, float]:
    """The width, height and frame rate of ``video``, from the file: a record's frame rate turns frames into seconds."""
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    try:
        width, height, rate = done.stdout.strip().split(",")
        over, under = rate.split("/")
        return int(width), int(height), int(over) / int(under)
    except (ValueError, ZeroDivisionError):
        raise StrictError(f"{video.name}: cannot read its stream: {done.stderr[-200:]}") from None


def _master_frames(video: Path, numbers: Iterable[int], size: int) -> dict[int, bytes]:
    """The frames ``numbers`` of ``video``, decoded to RGB, of ``size`` bytes each; one past its end is empty."""
    wanted = sorted(set(numbers))
    picked = "+".join(f"eq(n\\,{number})" for number in wanted)
    done = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select={picked}", "-fps_mode", "passthrough",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=False,
    )  # fmt: skip
    if done.returncode != 0:
        raise StrictError(f"{video.name}: cannot decode it: {done.stderr.decode(errors='replace')[-200:]}")
    return {n: done.stdout[i * size : (i + 1) * size] for i, n in enumerate(wanted)}


def _picture(path: Path) -> bytes:
    """The picture at ``path`` as RGB bytes, or nothing when it is no picture: it then matches no frame."""
    done = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=False,
    )  # fmt: skip
    return done.stdout if done.returncode == 0 else b""


# -- the gate ------------------------------------------------------------------------------------------------------
def _when(finding: Finding) -> tuple[float, float]:
    start = 0.0 if finding.start is None else finding.start
    return start, start if finding.end is None else finding.end


def _window_defect(entry: Cleared, finding: Finding, fps: float) -> str:
    """Why the frames measured are not the frames the report means, or nothing: a true number about the wrong text."""
    first, last = entry.measurement.first_frame / fps, (entry.measurement.last_frame + 1) / fps
    start, end = _when(finding)
    if first <= end + 1 / fps and start <= last:
        return ""
    measured = f"frames {entry.measurement.first_frame} to {entry.measurement.last_frame}"
    return f"{entry}: {measured} are not when the report says it was drawn, {start:.3f} to {end:.3f} s"


def _fit_defects(entry: Cleared, fit: Fit, finding: Finding, fps: float, size: tuple[int, int]) -> list[str]:
    """Why a text that fits at rest does not answer the report: the cut must be over by then, and inside the frame."""
    reasons = []
    end, rest = _when(finding)[1], fit.rest_frame / fps
    if end > rest + _SAME:
        reasons.append(
            f"{entry}: the report has it cut until {end:.3f} s, and frame {fit.rest_frame} at {rest:.3f} s is its rest"
        )
    width, height = size
    if fit.text[2] >= width or fit.text[3] >= height:
        reasons.append(f"{entry}: the text at {list(fit.text)} leaves the {width}x{height} frame")
    return reasons


def _entry_defects(entry: Cleared, finding: Finding, fps: float, size: tuple[int, int]) -> list[str]:
    reasons = []
    if finding.limit is None or abs(finding.limit - entry.measurement.minimum) > _SAME:
        minimum = entry.measurement.minimum
        reasons.append(f"{entry}: the record's minimum {minimum:g} is not the report's {finding.limit}")
    if window := _window_defect(entry, finding, fps):
        reasons.append(window)
    if isinstance(entry.measurement, Fit):
        reasons.extend(_fit_defects(entry, entry.measurement, finding, fps, size))
    return reasons


def _proof_defects(
    record: Record, report: Report, matched: Sequence[tuple[Cleared, Finding]], project: Path, video: Path
) -> list[str]:
    """Why ``record`` does not hold against the files, or nothing: every number here comes from them, not from it."""
    if record.scene_sha256 != report.scene_sha256:
        return ["the record was measured on another scene"]
    if not video.is_file():
        return ["no rendered video to prove its record on"]
    if record.video_sha256 != hashlib.sha256(video.read_bytes()).hexdigest():
        return ["the record was measured on another master"]
    width, height, fps = _stream(video)
    if abs(record.fps - fps) > _SAME:
        return [f"the record says {record.fps:g} fps, the master {fps:g}"]
    reasons = [reason for entry, finding in matched for reason in _entry_defects(entry, finding, fps, (width, height))]
    cited = [(entry, evidence) for entry, _ in matched for evidence in entry.frames]
    frames = _master_frames(video, (evidence.frame for _, evidence in cited), width * height * 3)
    for entry, evidence in cited:
        picture = project / evidence.path
        if not picture.is_file():
            reasons.append(f"{entry}: no evidence at {evidence.path}")
        elif not frames[evidence.frame] or _picture(picture) != frames[evidence.frame]:
            reasons.append(f"{entry}: {evidence.path} is not frame {evidence.frame} of the master")
    return reasons


def _reel_defects(release: Release, project: Path, video: Path, records: Path) -> list[str]:
    scene, report_path = project / release.scene_file, project / ENGINE_REPORT
    if not scene.is_file():
        return [f"no built scene at {project.name}/{release.scene_file}"]
    if not report_path.is_file():
        return [f"no render report at {project.name}/{ENGINE_REPORT}: encode it with --report"]
    report = read_report(report_path)
    document = scene.read_bytes()
    if report.scene_sha256 != hashlib.sha256(document).hexdigest():
        return ["the render report is of another scene: render it again"]
    duration = _duration(document)
    if abs(report.start) > _SAME or abs(report.end - duration) > _SAME:
        return [f"the render report covers {report.start:g} to {report.end:g} s of {duration:g} s"]
    path = records / f"{release.slug}.json"
    record = read_record(path) if path.is_file() else None
    entries = {entry.key: entry for entry in record.cleared} if record else {}
    found = {finding.key: finding for finding in report.findings}
    stale = [
        f"the record clears {entry.named}, which the report has not" for k, entry in entries.items() if k not in found
    ]
    open_ = [str(finding) for finding in report.findings if finding.key not in entries]
    matched = [(entry, found[key]) for key, entry in entries.items() if key in found]
    if record is None or not matched:
        return [*stale, *open_]
    return [*stale, *open_, *_proof_defects(record, report, matched, project, video)]


def strict_defects(
    releases: Mapping[str, Release], episodes: Path, renders: Path, first: Mapping[str, str], records: Path
) -> list[Drift]:
    """Each reel on its ``first`` delivery with a ``--strict`` finding its record does not prove false, or with no
    report to read: no report is not a clean report. A bad record refuses its own reel and leaves the others' alone."""
    drift: list[Drift] = []
    for slug, video in first.items():
        try:
            reasons = _reel_defects(
                releases[slug], Path(episodes) / slug, Path(renders) / f"{video}.mp4", Path(records)
            )
        except DeliveryError as e:
            reasons = [str(e)]
        drift.extend(Drift(video, reason) for reason in reasons)
    return drift


# -- the listing ---------------------------------------------------------------------------------------------------
def _lines(record: Record) -> Iterable[str]:
    yield f"{record.slug}: {len(record.cleared)} cleared, author {record.author}, reviewer {record.reviewer}"
    for entry in record.cleared:
        yield f"  {entry}: {entry.measurement}"
        for evidence in entry.frames:
            yield f"    frame {evidence.frame}: {evidence.path}"


def listing(records: Sequence[Record], releases: Mapping[str, Release], delivered: Mapping[str, object]) -> list[str]:
    """The reels shipped under the rule, each with its numbers and frames, and how often that is: the publishing side
    asked to see it, and a ``delivered:`` post carries the reel's lines."""
    shipped = [record for record in records if releases[record.slug].video_name in delivered]
    waiting = [record.slug for record in records if record not in shipped]
    summary = f"{len(shipped)} of {len(delivered)} delivered reels shipped under the strict rule"
    if waiting:
        summary += f"; {len(waiting)} record{'s' if len(waiting) > 1 else ''} waiting to deliver: {', '.join(waiting)}"
    return [*(line for record in shipped for line in _lines(record)), summary]
