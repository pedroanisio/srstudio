"""A dance style as targets: ranges derived from a reference dancer's measures, and the check that lists what one of
our dances misses (ADR 0203).

:func:`derive` turns a :class:`dance_study.StyleReading` of a reference into a :class:`DanceStyle`. Each channel's
targets are ranges, never single numbers: the middle half of the reference's windows (25th to 75th percentile),
widened by the estimate's own noise, and left out (None) where the reference gave too little evidence. The record is
``srstudio.dance-style/1.2.0``, strict JSON, and holds only these numbers: no frame, landmark or time of the reference.

1.1 added a gesture's timing (ADR 0204): per channel, ranges for the place of its fastest moment, its attack and
release in beats and its peak acceleration, and the mean velocity profile of one cycle with how far a dance's may lie
from it. They stand only on windows whose curve holds more than a sine, the profile only where those windows agree on
it, and the frames that repeated a picture are counted as refused (``repeat``).

1.2 adds each channel's provenance (ADR 0202) and the ``confidence`` that provenance allows: a channel read from the
estimator's 3D estimate (``estimated-3d``) is held at most ``fair`` whatever its ``trust`` (:data:`CONFIDENCE_CAP`),
and a miss weighs by that confidence. An ``unobserved`` channel is never a target: it has no ranges, the record refuses
one that has, and it is listed under ``unmeasured``.

Older records read with their own meaning. A 1.0 record has no timing, no ``repeat`` refusals and no ``timed``
windows; neither a 1.0 nor a 1.1 record stated a provenance, so their channels read with ``provenance`` and
``confidence`` None (missing, never filled in from today's channel table) and their misses weigh by ``trust``, as they
did when written. Such a record is never written back as 1.2: it would claim a provenance it never stated. A channel
the table now calls unobserved stays unobserved: an older record that holds a range on one is refused.

:func:`check` samples nothing itself: it takes any sequence of :class:`dance.DanceFrame` (a move, a routine, a
phrase), measures it on a preset skeleton with the same code as the reference, and returns :meth:`DanceStyle.misses`,
ranked by how much each matters: the channel's confidence (its trust, in a record older than 1.2), the measure's
weight, and how far outside the range it falls against the range's width.
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
from ._dance_measure import PROFILE_POINTS, profile_distance
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
    "SCHEMAS",
    "TIMING",
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

SCHEMA = "srstudio.dance-style/1.2.0"
SCHEMAS = ("srstudio.dance-style/1.0.0", "srstudio.dance-style/1.1.0", SCHEMA)  # oldest first
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
    "peak_speed_phase": 0.5,
    "attack": 0.5,
    "release": 0.5,
    "peak_acceleration": 0.4,
    "profile_distance": 0.6,
}
MEASURES = ("level", "peak_to_peak", "range", "cycles_per_beat", "snap_ratio", "hit_offset")
TIMING = ("peak_speed_phase", "attack", "release", "peak_acceleration")
TARGETS = (*MEASURES, *TIMING, "velocity", "profile_distance")  # every field a channel can be checked against
PROFILE_AGREE = 0.15  # windows whose velocity profiles lie further than this from their mean do not agree on one
ACCELERATION_WIDEN = 0.25  # a share of the middle peak acceleration: it is the fit's second derivative, the noisiest
FLOOR = {"head_radii": 0.05, "rad": 0.03, "ratio": 0.03, "head_radii_per_beat": 0.1}
MEASURE_FLOOR = {
    "cycles_per_beat": 0.05,
    "snap_ratio": 0.1,
    "hit_offset": 0.03,
    "lag": 0.03,
    "peak_speed_phase": 0.03,
    "attack": 0.03,
    "release": 0.03,
    "peak_acceleration": 1.0,
    "profile_distance": 0.03,
}
MAX_SEVERITY_GAP = 4.0  # a miss four widths out counts no more than one far further out
MIN_FRAMES = 30
CYCLE_WIDEN = 0.05
SNAP_WIDEN = 0.1  # a share of the middle snap ratio
NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
DIGEST = re.compile(r"[0-9a-f]{64}")
TEXT = re.compile(r"[^\x00-\x1f\x7f]{1,600}")
REJECTS = ("lost", "low_confidence", "implausible", "jump", "arm", "repeat")
WHOLE_FRAME = ("lost", "low_confidence", "implausible", "jump", "repeat")  # an arm left out leaves its frame in use
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

    The gesture's timing (1.1): ``peak_speed_phase`` (a share of the cycle from the hit, either way round the seam),
    ``attack`` and ``release`` in beats, ``peak_acceleration`` in amplitudes per beat squared; ``velocity`` the mean
    one-cycle velocity profile and ``profile_distance`` how far from it a dance's may lie.

    ``provenance`` is what the channel reads (1.2); ``confidence``, the lower of ``trust`` and what the provenance
    allows, is what its misses weigh by, and None for an ``unobserved`` channel, which holds no range. Both are None
    on a channel read from a record written before 1.2, which never stated them: :attr:`held` is then its ``trust``."""

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
    peak_speed_phase: Range | None = None
    attack: Range | None = None
    release: Range | None = None
    peak_acceleration: Range | None = None
    velocity: tuple[float, ...] | None = None
    profile_distance: Range | None = None
    provenance: str | None = None
    confidence: str | None = None

    def __post_init__(self) -> None:
        if self.provenance is None:  # an older record's channel: no provenance stated, so no confidence either
            if self.trust not in TRUST:
                raise StyleValueError(f"{self.name} trust is one of {list(TRUST)}", path=f"{self.name}.trust")
            if self.confidence is not None:
                raise StyleValueError(
                    f"{self.name} states no provenance: it holds no confidence, not {self.confidence!r}",
                    path=f"{self.name}.confidence",
                )
            return
        if self.provenance not in pt.PROVENANCES:
            raise StyleValueError(
                f"{self.name} provenance is one of {list(pt.PROVENANCES)}, not {self.provenance!r}",
                path=f"{self.name}.provenance",
            )
        if self.trust not in TRUST:
            raise StyleValueError(f"{self.name} trust is one of {list(TRUST)}", path=f"{self.name}.trust")
        if self.provenance == pt.UNOBSERVED:
            held = [m for m in TARGETS if getattr(self, m) is not None]
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

    @property
    def held(self) -> str | None:
        """The level its misses weigh by: the confidence, or the trust of a record that stated no provenance; None for
        an unobserved channel, which is no target."""
        return self.trust if self.provenance is None else self.confidence


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
            held = target.held
            if held is None:  # unobserved: no target
                continue
            ours = reading.channels[target.name]
            for measure in MEASURES + TIMING:
                span = getattr(target, measure)
                if span is not None:
                    found = _ours(ours, measure)
                    if measure == "peak_speed_phase" and found is not None:
                        found = _round(found, span)
                    out.extend(_miss(target.name, measure, target.unit, held, span, found))
            if target.velocity is not None and target.profile_distance is not None:
                away = profile_distance(ours.velocity, target.velocity) if ours.velocity else None
                out.extend(_miss(target.name, "profile_distance", "", held, target.profile_distance, away))
        for lag in self.lags:
            if lag.beats is not None:
                lagged = reading.lags[lag.key].beats
                out.extend(_miss(lag.key, "lag", "beats", "fair", lag.beats, lagged.p50 if lagged else None))
        return tuple(sorted(out, key=lambda m: (-m.severity, m.channel, m.measure)))


def _ours(reading: ChannelReading, measure: str) -> float | None:
    found: Spread | None = getattr(reading, measure)
    return None if found is None else found.p50


def _round(phase: float, span: Range) -> float:
    """The place ``phase`` reads as, whole cycles away, that lies nearest ``span``: a cycle has no seam."""
    middle = (span[0] + span[1]) / 2
    return phase + round(middle - phase)


def _miss(name: str, measure: str, unit: str, trust: str, span: Range, ours: float | None) -> list[StyleMiss]:
    low, high = span
    weight = TRUST[trust] * IMPORTANCE["lag" if measure == "lag" else measure]
    shown = unit if measure in ("level", "peak_to_peak", "range") else {"lag": "beats"}.get(measure, "")
    if ours is None:
        words = f"{name} {measure}: ours shows no steady cycle; the reference reads {low:.3f}..{high:.3f} {shown}"
        if measure in (*TIMING, "profile_distance"):
            words = (
                f"{name} {measure}: ours holds no more than a sine; the reference reads {low:.3f}..{high:.3f} {shown}"
            )
        return [StyleMiss(name, measure, None, low, high, round(weight, 4), trust, words.rstrip())]
    if low <= ours <= high:
        return []
    gap = low - ours if ours < low else ours - high
    floor = MEASURE_FLOOR.get(measure, FLOOR.get(unit, 0.05))
    width = max(high - low, 0.25 * abs(low + high) / 2, floor)
    severity = weight * min(MAX_SEVERITY_GAP, gap / width)
    way = {
        "hit_offset": ("early", "late"),
        "lag": ("early", "late"),
        "peak_speed_phase": ("early", "late"),
        "attack": ("quick", "slow"),
        "release": ("quick", "slow"),
    }.get(measure, ("small", "big"))
    word = way[0] if ours < low else way[1]
    words = f"{name} {measure} too {word}: ours {ours:.3f}, the reference {low:.3f}..{high:.3f} {shown}"
    if measure == "profile_distance":
        words = f"{name} velocity profile unlike the reference's: {ours:.3f} from its mean, at most {high:.3f}"
    return [StyleMiss(name, measure, ours, low, high, round(severity, 4), trust, words.rstrip())]


# --- deriving targets from a reference -----------------------------------------------------------------------------


def _span(spread: Spread | None, widen: float, enough: bool, floor: float | None = 0.0) -> Range | None:
    if spread is None or not enough:
        return None
    low, high = spread.p25 - widen, spread.p75 + widen
    if floor is not None:
        low = max(floor, low)
    return (math.floor(low * 1e4) / 1e4, math.ceil(high * 1e4) / 1e4)  # outward, so rounding never narrows it


_TimingTargets = tuple[Range | None, Range | None, Range | None, Range | None, tuple[float, ...] | None, Range | None]


def _timing_targets(reading: ChannelReading, frame_beats: float) -> _TimingTargets:
    """The timing ranges, on ``MIN_WINDOWS`` windows that read more than a sine, and the mean velocity profile with how
    far from it a dance's may lie, only where those windows agree on it. Only a channel of ``good`` trust, read in
    the picture's own plane, holds them: a timing read through the estimator's depth guess carries that guess's
    jitter in its second derivative."""
    timed = reading.timed >= MIN_WINDOWS and CHANNEL[reading.name].trust == "good"
    acceleration = reading.peak_acceleration.p50 * ACCELERATION_WIDEN if reading.peak_acceleration else 0.0
    cycle_frame = frame_beats * (reading.cycles_per_beat.p50 if reading.cycles_per_beat else 1.0)
    agreed = reading.profile_spread if timed and reading.velocity else None
    if agreed is not None and agreed.p75 > PROFILE_AGREE:
        agreed = None
    return (
        _span(reading.peak_speed_phase, cycle_frame / 2, timed, None),
        _span(reading.attack, frame_beats / 2, timed),
        _span(reading.release, frame_beats / 2, timed),
        _span(reading.peak_acceleration, acceleration, timed),
        None if agreed is None else tuple(round(v, 4) for v in reading.velocity),
        None if agreed is None else (0.0, math.ceil((agreed.p90 + PROFILE_AGREE) * 1e4) / 1e4),
    )


def _channel_target(reading: ChannelReading, frame_beats: float) -> ChannelTarget:
    chan = CHANNEL[reading.name]
    if chan.provenance == pt.UNOBSERVED:  # never a target: no range, whatever the reading says
        counts = {"frames": reading.frames, "windows": reading.windows, "read": 0, "still": 0, "locked": 0, "timed": 0}
        return ChannelTarget(
            reading.name, reading.unit, chan.trust, chan.why, None, None, None, None, None, None, None, counts,
            provenance=pt.UNOBSERVED,
        )  # fmt: skip
    # Sizes widen by twice the reading's noise, and by at least half the unit's floor: a difference smaller than the
    # floor does not show, and a range narrower than it would fail on the record's own rounding.
    widen = max(2 * (reading.noise or 0.0), FLOOR[reading.unit] / 2)
    grooves = reading.read >= MIN_WINDOWS
    strokes = reading.timed >= MIN_WINDOWS  # a sine's rise is its fall: only windows timed read a snap
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
        _span(reading.snap_ratio, snap, strokes, 0.01),
        _span(reading.hit_offset, frame_beats / 2, reading.locked >= MIN_WINDOWS, None),
        {
            "frames": reading.frames,
            "windows": reading.windows,
            "read": reading.read,
            "still": reading.still,
            "locked": reading.locked,
            "timed": reading.timed,
        },
        *_timing_targets(reading, frame_beats),
        provenance=chan.provenance,
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
    """The style as its strict JSON record, of the current schema."""
    unstated = [c.name for c in style.channels if c.provenance is None]
    if unstated:
        raise StyleValueError(
            f"{unstated} state no provenance (a record older than {SCHEMA}): written as {SCHEMA} they would claim one;"
            " derive the style again from its reference",
            path="channels",
        )
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
                **{m: _range_data(getattr(c, m)) for m in MEASURES + TIMING},
                "velocity": None if c.velocity is None else list(c.velocity),
                "profile_distance": _range_data(c.profile_distance),
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
    if top["schema"] not in SCHEMAS:
        kind = StyleSchemaError if isinstance(top["schema"], str) else StyleFormatError
        raise kind(f"schema is one of {list(SCHEMAS)}, not {top['schema']!r}", path="schema")
    timing = top["schema"] != SCHEMAS[0]
    stated = top["schema"] == SCHEMA  # provenance and confidence: 1.2 on
    generated = _fields(top["generated_by"], "generated_by", ("tool", "model"))
    items = _list(top["channels"], "channels", 64)
    channels = tuple(_channel(item, f"channels[{i}]", timing, stated) for i, item in enumerate(items))
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
        _reference(top["reference"], timing),
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
    "peak_speed_phase": (-1.0, 2.0),  # a share of the cycle, either side of its seam
    "attack": (0.0, 16.0),
    "release": (0.0, 16.0),
    "peak_acceleration": (0.0, 1e6),
    "profile_distance": (0.0, 2.0),
}
LEVEL_LIMITS = {
    "head_radii": (-50.0, 50.0),
    "rad": (-4.0, 4.0),
    "ratio": (0.0, 1.5),
    "head_radii_per_beat": (0.0, 200.0),
}


def _reference(value: object, timing: bool) -> Reference:
    keys = tuple(f.name for f in fields(Reference))
    ref = _fields(value, "reference", keys)
    reasons = REJECTS if timing else REJECTS[:-1]
    rejected = _fields(ref["rejected"], "reference.rejected", reasons)
    frames = _int(ref["frames"], "reference.frames", 1, 10_000_000)
    used = _int(ref["used"], "reference.used", 0, frames)
    counts = {k: _int(rejected[k], f"reference.rejected.{k}", 0, frames) for k in reasons} | (
        {} if timing else {"repeat": 0}
    )
    if used + sum(counts[k] for k in WHOLE_FRAME) > frames:
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


def _channel(value: object, path: str, timing: bool, stated: bool) -> ChannelTarget:
    added = ("provenance", "confidence") if stated else ()
    keys = ("name", "unit", "trust", *added, "why", "noise", *MEASURES, "evidence")
    entry = _fields(value, path, keys + ((*TIMING, "velocity", "profile_distance") if timing else ()))
    name = _text(entry["name"], f"{path}.name", NAME_DOTTED)
    if name not in CHANNEL:
        raise StyleValueError(f"{path} names no channel: {name!r}", path=f"{path}.name")
    chan = CHANNEL[name]
    if entry["unit"] != chan.unit:
        raise StyleValueError(f"{name} is measured in {chan.unit}, not {entry['unit']!r}", path=f"{path}.unit")
    if entry["trust"] not in TRUST:
        raise StyleValueError(f"{path}.trust is one of {list(TRUST)}", path=f"{path}.trust")
    counted = ("frames", "windows", "read", "still", "locked") + (("timed",) if timing else ())
    evidence = _fields(entry["evidence"], f"{path}.evidence", counted)
    counts = {k: _int(v, f"{path}.evidence.{k}", 0, 10_000_000) for k, v in evidence.items()} | (
        {} if timing else {"timed": 0}
    )
    if counts["read"] + counts["still"] > counts["windows"] or counts["locked"] > counts["read"]:
        raise StyleValueError(f"{path}.evidence counts more windows read than it has", path=f"{path}.evidence")
    if counts["timed"] > counts["read"]:
        raise StyleValueError(f"{path}.evidence has more windows timed than read", path=f"{path}.evidence")
    spans = {}
    for m in MEASURES + (TIMING + ("profile_distance",) if timing else ()):
        limits = LEVEL_LIMITS[chan.unit] if m == "level" else LIMITS[m]
        spans[m] = _range(entry[m], f"{path}.{m}", limits)
    velocity = _profile(entry["velocity"], f"{path}.velocity") if timing else None
    if (velocity is None) != (spans.get("profile_distance") is None):
        raise StyleValueError(f"{path}: velocity and profile_distance are given together", path=path)
    if not chan.groove and (any(spans[m] is not None for m in spans if m != "level") or velocity is not None):
        raise StyleValueError(f"{name} is read as a level, never as a groove", path=path)
    noise = None if entry["noise"] is None else _number(entry["noise"], f"{path}.noise", 0.0, 100.0)
    provenance, confidence = (entry["provenance"], entry["confidence"]) if stated else (None, None)
    if not stated and chan.provenance == pt.UNOBSERVED:
        held = [m for m in spans if spans[m] is not None] + (["velocity"] if velocity is not None else [])
        if held:
            raise StyleValueError(f"{name} is unobserved: an older record cannot make it a target ({held})", path=path)
    if stated and provenance != chan.provenance:
        raise StyleValueError(f"{name} reads {chan.provenance} data: its provenance is not {provenance!r}", path=path)
    if stated and provenance != pt.UNOBSERVED and confidence is None:
        raise StyleValueError(f"{path}.confidence is missing: {name} is observed", path=f"{path}.confidence")
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
        spans.get("peak_speed_phase"),
        spans.get("attack"),
        spans.get("release"),
        spans.get("peak_acceleration"),
        velocity,
        spans.get("profile_distance"),
        None if provenance is None else str(provenance),
        None if confidence is None else str(confidence),
    )


def _profile(value: object, path: str) -> tuple[float, ...] | None:
    if value is None:
        return None
    points = _list(value, path, PROFILE_POINTS)
    if len(points) != PROFILE_POINTS:
        raise StyleFormatError(f"{path} is {PROFILE_POINTS} numbers", path=path)
    return tuple(_number(v, path, -1.0, 1.0) for v in points)


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
