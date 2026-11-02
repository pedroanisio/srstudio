"""A dance style as targets: ranges derived from a reference dancer's measures, and the check that lists what one of
our dances misses (ADR 0203).

:func:`derive` turns a :class:`dance_study.StyleReading` of a reference into a :class:`DanceStyle`. Each channel's
targets are ranges, never single numbers: the middle half of the reference's windows (25th to 75th percentile),
widened by the estimate's own noise, and left out (None) where the reference gave too little evidence. The record is
``srstudio.dance-style/1.1.0``, strict JSON, and holds only these numbers: no frame, landmark or time of the reference.

Each channel carries the provenance of what it reads (ADR 0202) and the ``confidence`` that provenance allows: a
channel read from the estimator's 3D estimate (``estimated-3d``) is held at most ``fair`` whatever its ``trust``
(:data:`CONFIDENCE_CAP`), and a miss weighs by that confidence. An ``unobserved`` channel is never a target: it has no
ranges, the record refuses one that has, and it is listed under ``unmeasured``. A ``1.0.0`` record, written before
provenance, reads with each channel's provenance from :data:`dance_study.CHANNEL` and the confidence it allows.

:func:`check` samples nothing itself: it takes any sequence of :class:`dance.DanceFrame` (a move, a routine, a
phrase), measures it on a preset skeleton with the same code as the reference, and returns :meth:`DanceStyle.misses`,
ranked by how much each matters: the channel's trust, the measure's weight, and how far outside the range it falls
against the range's width.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from importlib import resources
from pathlib import Path

from . import pose_track as pt
from . import skeleton as sk
from ._dance_model import DanceError
from ._dance_sample import DanceFrame
from .dance_study import (
    CHANNEL,
    LAG_POINTS,
    LAGS,
    MIN_WINDOWS,
    UNMEASURED,
    ChannelReading,
    LagReading,
    Spread,
    StyleReading,
    dance_body,
    measure_style,
)
from .music import Groove

__all__ = [
    "CONFIDENCE_CAP",
    "IMPORTANCE",
    "SCHEMA",
    "TRUST",
    "ChannelTarget",
    "DanceStyle",
    "DanceStyleError",
    "LagTarget",
    "Reference",
    "StyleCheck",
    "StyleFormatError",
    "StyleMiss",
    "StyleSchemaError",
    "StyleValueError",
    "check",
    "derive",
    "dump_style",
    "load_style",
    "parse_style",
    "styles",
]

SCHEMA = "srstudio.dance-style/1.1.0"
LEGACY_SCHEMA = "srstudio.dance-style/1.0.0"  # before provenance: read, never written
MAX_BYTES = 1_000_000
TRUST = {"good": 1.0, "fair": 0.6, "poor": 0.25}
CONFIDENCE_CAP = {pt.MEASURED_2D: "good", pt.ESTIMATED_3D: "fair"}  # the most a channel of each provenance is held
IMPORTANCE = {
    "level": 1.0,
    "peak_to_peak": 1.0,
    "range": 0.8,
    "lag": 0.8,
    "cycles_per_beat": 0.7,
    "hit_offset": 0.6,
    "snap_ratio": 0.5,
}
MEASURES = ("level", "peak_to_peak", "range", "cycles_per_beat", "snap_ratio", "hit_offset")
FLOOR = {"head_radii": 0.05, "rad": 0.03, "ratio": 0.03, "head_radii_per_beat": 0.1}
MEASURE_FLOOR = {"cycles_per_beat": 0.05, "snap_ratio": 0.1, "hit_offset": 0.03, "lag": 0.03}
MAX_SEVERITY_GAP = 4.0  # a miss four widths out counts no more than one far further out
MIN_FRAMES = 30
CYCLE_WIDEN = 0.05
SNAP_WIDEN = 0.1  # a share of the middle snap ratio
NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
DIGEST = re.compile(r"[0-9a-f]{64}")
TEXT = re.compile(r"[^\x00-\x1f\x7f]{1,600}")
REJECTS = ("lost", "low_confidence", "implausible", "jump", "arm")
Range = tuple[float, float]


class DanceStyleError(DanceError):
    """A style record or a check that cannot be used."""


class StyleFormatError(DanceStyleError):
    """Not one strict JSON record of the style schema: bad JSON, an unknown or missing field, a wrong type."""


class StyleSchemaError(DanceStyleError):
    """A record of another schema or major."""


class StyleValueError(DanceStyleError):
    """Well formed, but a value out of range or two that contradict each other."""


@dataclass(frozen=True)
class Reference:
    """What the targets were measured on: a description (never the footage), its digest, the estimator, how many
    frames there were and were used, those refused by reason, and the beat grid."""

    description: str
    source_sha256: str
    estimator: str
    estimator_version: str
    model_sha256: str
    seconds: float
    frames: int
    used: int
    rejected: Mapping[str, int]
    bpm: float
    beats_per_bar: int
    offset_s: float


@dataclass(frozen=True)
class ChannelTarget:
    """A channel's ranges: ``level`` (its value), ``peak_to_peak`` (the groove's size), ``range`` (how far it travels in
    a window), ``cycles_per_beat``, ``snap_ratio`` (rise over fall) and ``hit_offset`` (beats from the beat); None
    where the reference could not say. ``evidence`` is how many frames and windows the ranges stand on.
    ``provenance`` is what the channel reads; ``confidence``, the lower of ``trust`` and what the provenance allows, is
    what its misses weigh by, and None for an ``unobserved`` channel, which holds no range."""

    name: str
    unit: str
    trust: str
    why: str
    noise: float | None
    level: Range | None
    peak_to_peak: Range | None
    range: Range | None
    cycles_per_beat: Range | None
    snap_ratio: Range | None
    hit_offset: Range | None
    evidence: Mapping[str, int]
    provenance: str = pt.ESTIMATED_3D
    confidence: str | None = None

    def __post_init__(self) -> None:
        if self.provenance not in pt.PROVENANCES:
            raise StyleValueError(
                f"{self.name} provenance is one of {list(pt.PROVENANCES)}, not {self.provenance!r}",
                path=f"{self.name}.provenance",
            )
        if self.trust not in TRUST:
            raise StyleValueError(f"{self.name} trust is one of {list(TRUST)}", path=f"{self.name}.trust")
        if self.provenance == pt.UNOBSERVED:
            held = [m for m in MEASURES if getattr(self, m) is not None]
            if held or self.confidence is not None:
                raise StyleValueError(
                    f"{self.name} is unobserved: it cannot be a target, and holds no range or confidence ({held})",
                    path=f"{self.name}.provenance",
                )
            return
        allowed = held_confidence(self.trust, self.provenance)
        if self.confidence is None:
            object.__setattr__(self, "confidence", allowed)
        elif self.confidence != allowed:
            raise StyleValueError(
                f"{self.name} confidence is {allowed!r}: trust {self.trust!r} held at most "
                f"{CONFIDENCE_CAP[self.provenance]!r} for {self.provenance}, not {self.confidence!r}",
                path=f"{self.name}.confidence",
            )


def held_confidence(trust: str, provenance: str) -> str:
    """The confidence a channel of ``trust`` is held at when it reads data of ``provenance``: the lower of the two."""
    order = list(TRUST)
    return order[max(order.index(trust), order.index(CONFIDENCE_CAP[provenance]))]


@dataclass(frozen=True)
class LagTarget:
    lead: str
    follow: str
    beats: Range | None
    evidence: Mapping[str, int]

    @property
    def key(self) -> str:
        return f"{self.lead}>{self.follow}"


@dataclass(frozen=True)
class StyleMiss:
    """One way a dance misses a style: the channel (or lag), the measure, ours (None when ours shows no such motion),
    the reference's range, how much it matters, and the miss in words."""

    channel: str
    measure: str
    ours: float | None
    low: float
    high: float
    severity: float
    trust: str
    words: str


@dataclass(frozen=True)
class DanceStyle:
    name: str
    description: str
    generated_by: Mapping[str, str]
    reference: Reference
    channels: tuple[ChannelTarget, ...]
    lags: tuple[LagTarget, ...]
    unmeasured: Mapping[str, str]

    def misses(self, reading: StyleReading) -> tuple[StyleMiss, ...]:
        """Each way ``reading`` misses this style, the one that matters most first; none means it dances the style."""
        if not isinstance(reading, StyleReading):
            raise DanceStyleError("a style checks a dance_study.StyleReading", path="reading")
        out = []
        for target in self.channels:
            if target.confidence is None:  # unobserved: no target
                continue
            ours = reading.channels[target.name]
            for measure in MEASURES:
                span = getattr(target, measure)
                if span is not None:
                    out.extend(_miss(target.name, measure, target.unit, target.confidence, span, _ours(ours, measure)))
        for lag in self.lags:
            if lag.beats is not None:
                found = reading.lags[lag.key].beats
                out.extend(_miss(lag.key, "lag", "beats", "fair", lag.beats, found.p50 if found else None))
        return tuple(sorted(out, key=lambda m: (-m.severity, m.channel, m.measure)))


def _ours(reading: ChannelReading, measure: str) -> float | None:
    found: Spread | None = getattr(reading, measure)
    return None if found is None else found.p50


def _miss(name: str, measure: str, unit: str, trust: str, span: Range, ours: float | None) -> list[StyleMiss]:
    low, high = span
    weight = TRUST[trust] * IMPORTANCE["lag" if measure == "lag" else measure]
    shown = unit if measure in ("level", "peak_to_peak", "range") else {"lag": "beats"}.get(measure, "")
    if ours is None:
        words = f"{name} {measure}: ours shows no steady cycle; the reference reads {low:.3f}..{high:.3f} {shown}"
        return [StyleMiss(name, measure, None, low, high, round(weight, 4), trust, words.rstrip())]
    if low <= ours <= high:
        return []
    gap = low - ours if ours < low else ours - high
    floor = MEASURE_FLOOR.get(measure, FLOOR.get(unit, 0.05))
    width = max(high - low, 0.25 * abs(low + high) / 2, floor)
    severity = weight * min(MAX_SEVERITY_GAP, gap / width)
    way = {"hit_offset": ("early", "late"), "lag": ("early", "late")}.get(measure, ("small", "big"))
    word = way[0] if ours < low else way[1]
    words = f"{name} {measure} too {word}: ours {ours:.3f}, the reference {low:.3f}..{high:.3f} {shown}"
    return [StyleMiss(name, measure, ours, low, high, round(severity, 4), trust, words.rstrip())]


# --- deriving targets from a reference -----------------------------------------------------------------------------


def _span(spread: Spread | None, widen: float, enough: bool, floor: float | None = 0.0) -> Range | None:
    if spread is None or not enough:
        return None
    low, high = spread.p25 - widen, spread.p75 + widen
    if floor is not None:
        low = max(floor, low)
    return (math.floor(low * 1e4) / 1e4, math.ceil(high * 1e4) / 1e4)  # outward, so rounding never narrows it


def _channel_target(reading: ChannelReading, frame_beats: float) -> ChannelTarget:
    chan = CHANNEL[reading.name]
    if chan.provenance == pt.UNOBSERVED:  # never a target: no range, whatever the reading says
        counts = {"frames": reading.frames, "windows": reading.windows, "read": 0, "still": 0, "locked": 0}
        return ChannelTarget(
            reading.name, reading.unit, chan.trust, chan.why, None, None, None, None, None, None, None, counts,
            pt.UNOBSERVED,
        )  # fmt: skip
    # Sizes widen by twice the reading's noise, and by at least half the unit's floor: a difference smaller than the
    # floor does not show, and a range narrower than it would fail on the record's own rounding.
    widen = max(2 * (reading.noise or 0.0), FLOOR[reading.unit] / 2)
    grooves = reading.read >= MIN_WINDOWS
    signed = reading.name in ("torso.lean", "torso.roll", "torso.twist", "shoulders.tilt", "head.sway", "arms.height")
    snap = reading.snap_ratio.p50 * SNAP_WIDEN if reading.snap_ratio else 0.0
    return ChannelTarget(
        reading.name,
        reading.unit,
        chan.trust,
        chan.why,
        None if reading.noise is None else round(reading.noise, 5),
        _span(reading.level, widen, reading.frames >= MIN_FRAMES, None if signed else 0.0),
        _span(reading.peak_to_peak, widen, reading.windows >= MIN_WINDOWS),
        _span(reading.range, widen, reading.windows >= MIN_WINDOWS),
        _span(reading.cycles_per_beat, CYCLE_WIDEN, grooves, 0.01),
        _span(reading.snap_ratio, snap, grooves, 0.01),
        _span(reading.hit_offset, frame_beats / 2, reading.locked >= MIN_WINDOWS, None),
        {
            "frames": reading.frames,
            "windows": reading.windows,
            "read": reading.read,
            "still": reading.still,
            "locked": reading.locked,
        },
        chan.provenance,
    )


def _lag_target(reading: LagReading, frame_beats: float) -> LagTarget:
    return LagTarget(
        reading.lead,
        reading.follow,
        _span(reading.beats, frame_beats / 2, reading.read >= MIN_WINDOWS, None),
        {"windows": reading.windows, "read": reading.read},
    )


def derive(
    reading: StyleReading, *, name: str, description: str, reference: Reference, generated_by: Mapping[str, str]
) -> DanceStyle:
    """A style from a reference's reading: every channel's and lag's ranges, and the channels no reading can measure."""
    if not isinstance(reading, StyleReading):
        raise DanceStyleError("a style is derived from a dance_study.StyleReading", path="reading")
    frame_beats = 1 / (reading.fps * 60 / reading.bpm)
    style = DanceStyle(
        name,
        description,
        dict(generated_by),
        reference,
        tuple(_channel_target(reading.channels[c], frame_beats) for c in CHANNEL),
        tuple(_lag_target(reading.lags[f"{a}>{b}"], frame_beats) for a, b in LAGS),
        dict(UNMEASURED) | {c.name: f"unobserved: {c.why}" for c in CHANNEL.values() if c.provenance == pt.UNOBSERVED},
    )
    return parse_style(dump_style(style))  # the record it writes is the record it reads


# --- the record ----------------------------------------------------------------------------------------------------


def _range_data(span: Range | None) -> list[float] | None:
    return None if span is None else [span[0], span[1]]


def dump_style(style: DanceStyle) -> str:
    """The style as its strict JSON record."""
    ref = style.reference
    data = {
        "schema": SCHEMA,
        "name": style.name,
        "description": style.description,
        "generated_by": dict(style.generated_by),
        "reference": {
            "description": ref.description,
            "source_sha256": ref.source_sha256,
            "estimator": ref.estimator,
            "estimator_version": ref.estimator_version,
            "model_sha256": ref.model_sha256,
            "seconds": ref.seconds,
            "frames": ref.frames,
            "used": ref.used,
            "rejected": dict(ref.rejected),
            "bpm": ref.bpm,
            "beats_per_bar": ref.beats_per_bar,
            "offset_s": ref.offset_s,
        },
        "channels": [
            {
                "name": c.name,
                "unit": c.unit,
                "trust": c.trust,
                "provenance": c.provenance,
                "confidence": c.confidence,
                "why": c.why,
                "noise": c.noise,
                **{m: _range_data(getattr(c, m)) for m in MEASURES},
                "evidence": dict(c.evidence),
            }
            for c in style.channels
        ],
        "lags": [
            {"lead": g.lead, "follow": g.follow, "beats": _range_data(g.beats), "evidence": dict(g.evidence)}
            for g in style.lags
        ],
        "unmeasured": [{"channel": k, "why": v} for k, v in style.unmeasured.items()],
    }
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def load_style(path: str | Path) -> DanceStyle:
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise StyleFormatError(f"cannot read the style record {path}: {error}", path="record") from None
    return parse_style(raw)


def styles(folder: Path | None = None) -> dict[str, DanceStyle]:
    """The measured styles in ``folder`` (the ones srstudio ships by default), by name; each file is named after its
    style."""
    where = resources.files("srstudio").joinpath("assets/dance/styles") if folder is None else folder
    found = {}
    for item in sorted(where.iterdir(), key=lambda i: i.name):
        if item.name.endswith(".json"):
            style = parse_style(item.read_bytes())
            if item.name != f"{style.name}.json":
                raise StyleValueError(f"{item.name} holds the style {style.name!r}", path="name")
            found[style.name] = style
    return found


def parse_style(text: str | bytes) -> DanceStyle:
    """A style from its JSON text: strict JSON of at most ``MAX_BYTES``, every field known and typed, every range in
    order and inside what its measure can be."""
    if len(text) > MAX_BYTES:
        raise StyleFormatError(f"a style record is at most {MAX_BYTES} bytes", path="record")
    try:
        data = json.loads(text, parse_constant=_no_constant, object_pairs_hook=_unique)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise StyleFormatError(f"a style record is one JSON object: {error}", path="record") from None
    top = _fields(
        data, "record", ("schema", "name", "description", "generated_by", "reference", "channels", "lags", "unmeasured")
    )
    if top["schema"] not in (SCHEMA, LEGACY_SCHEMA):
        kind = StyleSchemaError if isinstance(top["schema"], str) else StyleFormatError
        raise kind(f"schema is {SCHEMA} (or {LEGACY_SCHEMA}), not {top['schema']!r}", path="schema")
    legacy = top["schema"] == LEGACY_SCHEMA
    generated = _fields(top["generated_by"], "generated_by", ("tool", "model"))
    items = _list(top["channels"], "channels", 64)
    channels = tuple(_channel(item, f"channels[{i}]", legacy) for i, item in enumerate(items))
    if [c.name for c in channels] != list(CHANNEL):
        raise StyleValueError(f"channels are {list(CHANNEL)}, in that order", path="channels")
    lags = tuple(_lag(item, f"lags[{i}]") for i, item in enumerate(_list(top["lags"], "lags", 16)))
    if [g.key for g in lags] != [f"{a}>{b}" for a, b in LAGS]:
        raise StyleValueError(f"lags are {[f'{a}>{b}' for a, b in LAGS]}, in that order", path="lags")
    unmeasured = {}
    for i, item in enumerate(_list(top["unmeasured"], "unmeasured", 16)):
        entry = _fields(item, f"unmeasured[{i}]", ("channel", "why"))
        unmeasured[_text(entry["channel"], f"unmeasured[{i}].channel", NAME_DOTTED)] = _text(
            entry["why"], f"unmeasured[{i}].why"
        )
    return DanceStyle(
        _text(top["name"], "name", NAME),
        _text(top["description"], "description"),
        {
            "tool": _text(generated["tool"], "generated_by.tool"),
            "model": _text(generated["model"], "generated_by.model"),
        },
        _reference(top["reference"]),
        channels,
        lags,
        unmeasured,
    )


NAME_DOTTED = re.compile(r"[a-z][a-z_]*\.[a-z][a-z_]*")
LIMITS = {  # what each measure can be: (low, high)
    "peak_to_peak": (0.0, 100.0),
    "range": (0.0, 100.0),
    "cycles_per_beat": (0.0, 16.0),
    "snap_ratio": (0.0, 100.0),
    "hit_offset": (-1.0, 1.0),
    "lag": (-1.0, 1.0),
}
LEVEL_LIMITS = {
    "head_radii": (-50.0, 50.0),
    "rad": (-4.0, 4.0),
    "ratio": (0.0, 1.5),
    "head_radii_per_beat": (0.0, 200.0),
}


def _reference(value: object) -> Reference:
    keys = tuple(f.name for f in fields(Reference))
    ref = _fields(value, "reference", keys)
    rejected = _fields(ref["rejected"], "reference.rejected", REJECTS)
    frames = _int(ref["frames"], "reference.frames", 1, 10_000_000)
    used = _int(ref["used"], "reference.used", 0, frames)
    counts = {k: _int(rejected[k], f"reference.rejected.{k}", 0, frames) for k in REJECTS}
    if used + sum(counts[k] for k in REJECTS[:4]) > frames:  # an arm left out leaves its frame in use
        raise StyleValueError("used and refused frames add up to more than the reference holds", path="reference")
    return Reference(
        _text(ref["description"], "reference.description"),
        _text(ref["source_sha256"], "reference.source_sha256", DIGEST),
        _text(ref["estimator"], "reference.estimator"),
        _text(ref["estimator_version"], "reference.estimator_version"),
        _text(ref["model_sha256"], "reference.model_sha256", DIGEST),
        _number(ref["seconds"], "reference.seconds", 0.0, 1e6),
        frames,
        used,
        counts,
        _number(ref["bpm"], "reference.bpm", 30.0, 300.0),
        _int(ref["beats_per_bar"], "reference.beats_per_bar", 1, 16),
        _number(ref["offset_s"], "reference.offset_s", 0.0, 1e4),
    )


def _channel(value: object, path: str, legacy: bool = False) -> ChannelTarget:
    added = () if legacy else ("provenance", "confidence")
    keys = ("name", "unit", "trust", *added, "why", "noise", *MEASURES, "evidence")
    entry = _fields(value, path, keys)
    name = _text(entry["name"], f"{path}.name", NAME_DOTTED)
    if name not in CHANNEL:
        raise StyleValueError(f"{path} names no channel: {name!r}", path=f"{path}.name")
    chan = CHANNEL[name]
    if entry["unit"] != chan.unit:
        raise StyleValueError(f"{name} is measured in {chan.unit}, not {entry['unit']!r}", path=f"{path}.unit")
    if entry["trust"] not in TRUST:
        raise StyleValueError(f"{path}.trust is one of {list(TRUST)}", path=f"{path}.trust")
    evidence = _fields(entry["evidence"], f"{path}.evidence", ("frames", "windows", "read", "still", "locked"))
    counts = {k: _int(v, f"{path}.evidence.{k}", 0, 10_000_000) for k, v in evidence.items()}
    if counts["read"] + counts["still"] > counts["windows"] or counts["locked"] > counts["read"]:
        raise StyleValueError(f"{path}.evidence counts more windows read than it has", path=f"{path}.evidence")
    spans = {}
    for m in MEASURES:
        limits = LEVEL_LIMITS[chan.unit] if m == "level" else LIMITS[m]
        spans[m] = _range(entry[m], f"{path}.{m}", limits)
    if not chan.groove and any(spans[m] is not None for m in MEASURES[1:]):
        raise StyleValueError(f"{name} is read as a level, never as a groove", path=path)
    noise = None if entry["noise"] is None else _number(entry["noise"], f"{path}.noise", 0.0, 100.0)
    provenance = chan.provenance if legacy else entry["provenance"]
    if provenance != chan.provenance:
        raise StyleValueError(f"{name} reads {chan.provenance} data: its provenance is not {provenance!r}", path=path)
    confidence = None if legacy else entry["confidence"]
    if confidence is not None and confidence not in TRUST:
        raise StyleValueError(f"{path}.confidence is one of {list(TRUST)} or null", path=f"{path}.confidence")
    return ChannelTarget(
        name,
        chan.unit,
        str(entry["trust"]),
        _text(entry["why"], f"{path}.why"),
        noise,
        spans["level"],
        spans["peak_to_peak"],
        spans["range"],
        spans["cycles_per_beat"],
        spans["snap_ratio"],
        spans["hit_offset"],
        counts,
        str(provenance),
        None if confidence is None else str(confidence),
    )


def _lag(value: object, path: str) -> LagTarget:
    entry = _fields(value, path, ("lead", "follow", "beats", "evidence"))
    lead, follow = entry["lead"], entry["follow"]
    if lead not in LAG_POINTS or follow not in LAG_POINTS:
        raise StyleValueError(f"{path} names parts of {list(LAG_POINTS)}", path=path)
    evidence = _fields(entry["evidence"], f"{path}.evidence", ("windows", "read"))
    counts = {k: _int(v, f"{path}.evidence.{k}", 0, 10_000_000) for k, v in evidence.items()}
    if counts["read"] > counts["windows"]:
        raise StyleValueError(f"{path}.evidence reads more windows than it has", path=f"{path}.evidence")
    return LagTarget(str(lead), str(follow), _range(entry["beats"], f"{path}.beats", LIMITS["lag"]), counts)


def _range(value: object, path: str, limits: tuple[float, float]) -> Range | None:
    if value is None:
        return None
    pair = _list(value, path, 2)
    if len(pair) != 2:
        raise StyleFormatError(f"{path} is [low, high]", path=path)
    low, high = (_number(v, path, *limits) for v in pair)
    if low > high:
        raise StyleValueError(f"{path} {pair} is an ordered range", path=path)
    return (low, high)


def _no_constant(name: str) -> object:
    raise StyleFormatError(f"a style record holds finite numbers only, not {name}", path="record")


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise StyleFormatError(f"the key {key!r} is repeated", path=key)
        out[key] = value
    return out


def _fields(value: object, path: str, keys: tuple[str, ...]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise StyleFormatError(f"{path} is a JSON object", path=path)
    unknown = sorted(set(value) - set(keys))
    missing = [k for k in keys if k not in value]
    if unknown or missing:
        raise StyleFormatError(f"{path}: unknown field(s) {unknown}, missing field(s) {missing}", path=path)
    return value


def _list(value: object, path: str, most: int) -> list[object]:
    if not isinstance(value, list) or len(value) > most:
        raise StyleFormatError(f"{path} is a JSON list of at most {most} items", path=path)
    return value


def _number(value: object, path: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise StyleFormatError(f"{path} is a finite number, not {value!r}", path=path)
    if not low <= value <= high:
        raise StyleValueError(f"{path} {value} lies in {low}..{high}", path=path, actual=value)
    return float(value)


def _int(value: object, path: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StyleFormatError(f"{path} is a whole number, not {value!r}", path=path)
    if not low <= value <= high:
        raise StyleValueError(f"{path} {value} lies in {low}..{high}", path=path, actual=value)
    return value


def _text(value: object, path: str, pattern: re.Pattern[str] = TEXT) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise StyleFormatError(f"{path} is text matching {pattern.pattern}", path=path)
    return value


# --- checking one of ours ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StyleCheck:
    reading: StyleReading
    misses: tuple[StyleMiss, ...]

    @property
    def score(self) -> float:
        """The misses' severities summed: lower is closer to the style."""
        return round(sum(m.severity for m in self.misses), 4)


def check(
    style: DanceStyle,
    frames: Sequence[DanceFrame],
    groove: Groove,
    fps: int,
    *,
    profile: sk.SkeletonProfile | None = None,
    base: sk.SkeletonPose | None = None,
    clamp: bool = True,
) -> StyleCheck:
    """``frames`` of one of our dances, danced on ``profile`` (realistic by default) and measured on ``groove`` as the
    reference was, against ``style``."""
    if not isinstance(style, DanceStyle):
        raise DanceStyleError("a dance is checked against a DanceStyle", path="style")
    reading = measure_style(dance_body(frames, fps, profile=profile, base=base, clamp=clamp), groove)
    return StyleCheck(reading, style.misses(reading))
