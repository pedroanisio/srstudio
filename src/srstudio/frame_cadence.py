"""Every held key in a scene shows on the frame it was keyed for: none held over a frame, none skipped.

A scene writes key times to :data:`KEY_DIGITS` decimals. A key meant for frame ``f`` at ``f / fps`` can come out a
hair past that frame's time: at 30 fps, ``f / 30`` rounds up whenever ``f mod 3 = 2`` (2 / 30 = 0.0666666... is
written 0.066667). The engine samples frame ``f`` at ``f / fps`` and shows the last key at or before it, so on that
frame a held track still shows the key before: the drawing holds for a frame and then jumps two. A per-frame track
keyed from a time on the frame grid repeats one frame in three that way: a 10 Hz judder no still shows, and no check
that reads the build's own record of what it meant to draw can see, because the record is right and the scene is not.

This check reads every held track from the scene XML and samples it at each output frame the way the engine does:

- **shown** is the last key whose written time is at or before ``f / fps``;
- **intended** is the last key whose written time is at or before ``f / fps`` plus :data:`WRITE_TOL`, the most a
  6-decimal write can move a time: a key within that of a frame was keyed for that frame.

On a frame where the node is visible and the shown key holds (its segment is ``hold`` or ``step``) and differs in
value from the intended one, the frame is **held over** (:data:`HELD_OVER`), and the intended key, if no judged
frame ever shows it, is **skipped** (:data:`SKIPPED`). An interpolated segment is never judged: a write's rounding
moves it by under a microsecond. A node is visible on a frame when neither it nor any ancestor has a static
``opacity`` of 0 or ``visible="false"``, and every ``opacity`` or ``visible`` track on them gives a value above 0
there (an interpolated opacity counts as visible between two keys while either end is above 0).

Keys on a local time base are refused (:class:`CadenceError`, ``cadence.timebase``): this check samples the
composition clock only. Malformed scenes raise :class:`CadenceError` with a ``cadence.*`` code.

The fix the check asks for is to key a held track at frame centres, ``(f - 0.5) / fps``: half a frame from any
boundary, where no write's rounding reaches.

**The rendered rhythm** (:func:`even_change`) is the same defect seen from the pictures, and it sits here beside the
scene check because both judge one thing, whether each frame shows its own moment. It takes how much the picture
changed from each frame to the next (any measure: pixels of a figure mask that flip, say) and the shots, and groups
each shot's changes by ``f mod 3``. A pose held over one frame in three leaves that class with almost no change and
the next with a double one; a motion shown frame by frame leaves the three alike. A shot is even when its smallest
class median is at least :data:`EVEN_RATIO` of its largest (a still shot is even), and judged only with
:data:`MIN_PER_CLASS` frames in each class; the change across a cut is not counted. The report is clean when no shot
is uneven and at least one was judged, so a run with nothing to compare never passes. Running it on every shot gives
each one the others as its control.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .errors import SrstudioError

__all__ = [
    "EVEN_RATIO",
    "HELD_OVER",
    "MIN_PER_CLASS",
    "RhythmReport",
    "ShotRhythm",
    "even_change",
    "KEY_DIGITS",
    "SKIPPED",
    "WRITE_TOL",
    "CadenceError",
    "CadenceFinding",
    "CadenceReport",
    "HeldKey",
    "HeldTrack",
    "ScenePlan",
    "check",
    "read",
]

KEY_DIGITS = 6  # decimals a scene writes a key time to
WRITE_TOL = 0.5 * 10.0**-KEY_DIGITS  # seconds: the most such a write moves a time
HELD_OVER = "held-over"
SKIPPED = "skipped"
_HELD = frozenset({"hold", "step"})
_VISIBILITY = frozenset({"opacity", "visible"})
_GENERATED_ID = re.compile(r"n\d+")
EVEN_RATIO = 0.5  # smallest over largest median of a shot's three f mod 3 classes; a hold in three measured 0.11
MIN_PER_CLASS = 8  # frames each class needs before a shot is judged


class CadenceError(SrstudioError, ValueError):
    """A scene the cadence check cannot read."""


@dataclass(frozen=True)
class HeldKey:
    time: float
    value: str
    held: bool  # the segment after this key holds its value


@dataclass(frozen=True)
class HeldTrack:
    owner: str  # the nearest named node at or above the animated one ("" when none)
    node: str  # the animated node's id ("" when it has none)
    prop: str
    keys: tuple[HeldKey, ...]


@dataclass(frozen=True)
class ScenePlan:
    fps: float
    frames: int
    tracks: tuple[HeldTrack, ...]


@dataclass(frozen=True)
class CadenceFinding:
    owner: str
    node: str
    prop: str
    frame: int
    kind: str  # HELD_OVER or SKIPPED
    shown: int  # index of the key the frame shows
    intended: int  # index of the key keyed for the frame


@dataclass(frozen=True)
class CadenceReport:
    frames: int
    tracks: int
    findings: tuple[CadenceFinding, ...]

    @property
    def clean(self) -> bool:
        return not self.findings

    def frames_flagged(self, owner: str | None = None) -> tuple[int, ...]:
        """Every frame with a finding, of one owner when given."""
        return tuple(sorted({f.frame for f in self.findings if owner is None or f.owner == owner}))

    def owners(self) -> tuple[str, ...]:
        return tuple(sorted({f.owner for f in self.findings}))


def _err(message: str, code: str, **kw: object) -> CadenceError:
    return CadenceError(message, code=code, **kw)  # type: ignore[arg-type]


def _float(text: str | None, what: str, code: str) -> float:
    try:
        value = float(text) if text is not None else math.nan
    except ValueError:
        value = math.nan
    if not math.isfinite(value):
        raise _err(f"{what} must be a finite number, got {text!r}", code, actual=text)
    return value


@dataclass(frozen=True)
class _Track:
    node: ET.Element
    prop: str
    keys: tuple[HeldKey, ...]


def _keys(anim: ET.Element) -> tuple[HeldKey, ...]:
    base = anim.get("timeBase", "composition")
    if base != "composition":
        raise _err(f"keys on {anim.get('property')!r} use the {base!r} time base", "cadence.timebase", actual=base)
    default = anim.get("defaultInterpolation", "linear")
    keys: list[HeldKey] = []
    for k in anim:
        if k.tag != "key":
            continue
        t = _float(k.get("time"), f"a key time on {anim.get('property')!r}", "cadence.time")
        if keys and t < keys[-1].time:
            raise _err(f"key times on {anim.get('property')!r} go back from {keys[-1].time} to {t}", "cadence.order")
        keys.append(HeldKey(t, k.get("value", ""), k.get("interpolation", default) in _HELD))
    if not keys:
        raise _err(f"an animation of {anim.get('property')!r} has no keys", "cadence.keys")
    return tuple(keys)


def _visibility_value(prop: str, value: str) -> float:
    if prop == "visible":
        if value not in ("true", "false"):
            raise _err(f"visible must be true or false, got {value!r}", "cadence.value", actual=value)
        return 1.0 if value == "true" else 0.0
    return _float(value, "an opacity", "cadence.value")


def _last(keys: tuple[HeldKey, ...], t: float) -> int:
    """Index of the last key at or before ``t``; the first key holds before it starts."""
    i = 0
    for j, k in enumerate(keys):
        if k.time <= t:
            i = j
        else:
            break
    return i


def _shown_above_zero(prop: str, keys: tuple[HeldKey, ...], t: float) -> bool:
    i = _last(keys, t)
    here = _visibility_value(prop, keys[i].value)
    if keys[i].time > t or keys[i].held or i == len(keys) - 1 or keys[i].time == t:
        return here > 0
    return here > 0 or _visibility_value(prop, keys[i + 1].value) > 0


def _parse(xml: str | bytes) -> tuple[float, int, ET.Element]:
    if not isinstance(xml, (str, bytes)):
        raise _err(f"a scene is XML text or bytes, got {type(xml).__name__}", "cadence.input", actual=type(xml))
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise _err(f"the scene is not XML: {e}", "cadence.xml") from e
    if root.tag != "scene":
        raise _err(f"the root is <{root.tag}>, not <scene>", "cadence.root", actual=root.tag)
    project = root.find("project")
    if project is None:
        raise _err("the scene has no <project>", "cadence.project")
    fps = _float(project.get("fps"), "the project's fps", "cadence.project")
    duration = _float(project.get("duration"), "the project's duration", "cadence.project")
    if fps <= 0 or duration <= 0:
        raise _err(f"fps {fps} and duration {duration} must be above 0", "cadence.project")
    return fps, round(duration * fps), root


def _walk(root: ET.Element):
    """Every node with its ancestors (nearest first) and its tracks, static visibility read and checked."""
    parent = {c: p for p in root.iter() for c in p}
    tracks: dict[ET.Element, list[_Track]] = {}
    for anim in root.iter("animate"):
        node = parent[anim]
        tracks.setdefault(node, []).append(_Track(node, anim.get("property", ""), _keys(anim)))
    for node in root.iter():
        if node.get("opacity") is not None:
            _float(node.get("opacity"), "an opacity", "cadence.value")
        for t in tracks.get(node, ()):
            if t.prop in _VISIBILITY:
                for k in t.keys:
                    _visibility_value(t.prop, k.value)
    return parent, tracks


def _chain(parent: dict[ET.Element, ET.Element], node: ET.Element) -> list[ET.Element]:
    out = []
    e: ET.Element | None = node
    while e is not None:
        out.append(e)
        e = parent.get(e)
    return out


def _owner(chain: list[ET.Element]) -> str:
    for e in chain:
        i = e.get("id") or ""
        if i and not _GENERATED_ID.fullmatch(i):
            return i
    return ""


def read(xml: str | bytes) -> ScenePlan:
    """The scene's frame grid and every track with a held segment."""
    fps, frames, root = _parse(xml)
    parent, tracks = _walk(root)
    held = []
    for node, ts in tracks.items():
        for t in ts:
            if any(k.held for k in t.keys):
                held.append(HeldTrack(_owner(_chain(parent, node)), node.get("id", ""), t.prop, t.keys))
    return ScenePlan(fps, frames, tuple(held))


def check(xml: str | bytes) -> CadenceReport:
    """Sample every held track at each output frame as the engine does; see the module docstring."""
    fps, frames, root = _parse(xml)
    parent, tracks = _walk(root)
    times = [f / fps for f in range(frames)]
    seen: dict[ET.Element, list[bool]] = {}

    def visible(node: ET.Element) -> list[bool]:
        if node in seen:
            return seen[node]
        up = parent.get(node)
        above = visible(up) if up is not None else [True] * frames
        static = node.get("opacity") is None or float(node.get("opacity", "1")) > 0
        static = static and node.get("visible", "true") != "false"
        own = [False] * frames if not static else list(above)
        for t in tracks.get(node, ()):
            if t.prop in _VISIBILITY:
                own = [v and _shown_above_zero(t.prop, t.keys, s) for v, s in zip(own, times, strict=True)]
        seen[node] = own
        return own

    findings: list[CadenceFinding] = []
    judged = 0
    for node, ts in tracks.items():
        chain = _chain(parent, node)
        owner, nid = _owner(chain), node.get("id", "")
        on = visible(node)
        for t in ts:
            if not any(k.held for k in t.keys):
                continue
            judged += 1
            held_over: list[CadenceFinding] = []
            shown_any: set[int] = set()
            for f, s in enumerate(times):
                if not on[f]:
                    continue
                shown, intended = _last(t.keys, s), _last(t.keys, s + WRITE_TOL)
                shown_any.add(shown)
                if shown != intended and t.keys[shown].held and t.keys[shown].value != t.keys[intended].value:
                    held_over.append(CadenceFinding(owner, nid, t.prop, f, HELD_OVER, shown, intended))
            findings += held_over
            findings += [
                CadenceFinding(owner, nid, t.prop, h.frame, SKIPPED, h.shown, h.intended)
                for h in held_over
                if h.intended not in shown_any
            ]
    findings.sort(key=lambda x: (x.owner, x.node, x.prop, x.frame, x.kind))
    return CadenceReport(frames, judged, tuple(findings))


@dataclass(frozen=True)
class ShotRhythm:
    shot: int
    first: int  # the shot's first frame; its change from the frame before (a cut) is not counted
    last: int
    medians: tuple[float, float, float]  # median change of the frames f mod 3 = 0, 1, 2 (nan with none)
    counts: tuple[int, int, int]
    ratio: float | None  # smallest over largest median; None when not judged
    even: bool | None  # None when a class has fewer than MIN_PER_CLASS frames


@dataclass(frozen=True)
class RhythmReport:
    shots: tuple[ShotRhythm, ...]

    @property
    def clean(self) -> bool:
        return any(s.even is not None for s in self.shots) and not self.failing()

    def failing(self) -> tuple[int, ...]:
        return tuple(s.shot for s in self.shots if s.even is False)


def _median(values: list[float]) -> float:
    if not values:
        return math.nan
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def even_change(change: dict[int, float], shots: list[tuple[int, int]]) -> RhythmReport:
    """``change[f]``: how much the picture changed from frame ``f - 1`` to ``f``; ``shots``: each shot's first and
    last frame, in order and apart. See the module docstring."""
    if not shots:
        raise _err("no shots to judge", "rhythm.shots")
    prev_last = None
    for first, last in shots:
        if isinstance(first, bool) or isinstance(last, bool) or not isinstance(first, int) or not isinstance(last, int):
            raise _err(f"a shot is two frame numbers, got {(first, last)!r}", "rhythm.shots", actual=(first, last))
        if last < first or (prev_last is not None and first <= prev_last):
            raise _err(f"shots must run forward without overlap, got {(first, last)}", "rhythm.shots")
        prev_last = last
    for f, v in change.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise _err(f"the change at frame {f} must be a finite number from 0, got {v!r}", "rhythm.change", actual=v)
    out = []
    for i, (first, last) in enumerate(shots):
        classes: list[list[float]] = [[], [], []]
        for f in range(first + 1, last + 1):
            if f not in change:
                raise _err(f"no change measured at frame {f}", "rhythm.missing", actual=f)
            classes[f % 3].append(float(change[f]))
        medians = tuple(_median(c) for c in classes)
        counts = tuple(len(c) for c in classes)
        ratio: float | None = None
        even: bool | None = None
        if min(counts) >= MIN_PER_CLASS:
            top = max(medians)
            ratio = 1.0 if top == 0 else min(medians) / top
            even = ratio >= EVEN_RATIO
        out.append(ShotRhythm(i, first, last, medians, counts, ratio, even))  # type: ignore[arg-type]
    return RhythmReport(tuple(out))
