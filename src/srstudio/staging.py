"""The staged-reel toolkit every sequence style shares: a recorded take timeline staged shot by shot (ADR 0031).

A style's reel module keeps what is its own (its stage fields, its cast and sets, what a shot draws) and calls these
for the rest, so a fix to a camera move or a crossfade reaches every style:

* :func:`check_cover`, :func:`check_move` and :func:`check_spans` refuse a staging that does not fit the recording,
  in the style's own error class;
* :func:`rig` is the camera: a framed group that moves (:class:`Move`) holding a group that shakes (:func:`shake`);
  :func:`blackout` blacks the frame out in spans;
* :func:`crossfades` times the crossfade into a closing card, and :func:`close` draws the transitions, the engine's
  captions and the mix of the takes and the music bed, ducked under every line;
* :func:`freeze` holds a drawn shot still: every animated property at its value at the shot's start.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import camera, checks, native
from .errors import SrstudioError

__all__ = [
    "StagingError",
    "Move",
    "SHAKE_STEP",
    "SHAKE_PX",
    "CROSSFADE",
    "inside",
    "check_cover",
    "check_move",
    "check_spans",
    "rig",
    "shake",
    "blackout",
    "freeze",
    "crossfades",
    "close",
]

SHAKE_STEP = 1 / 12  # s between the shake's keys
SHAKE_PX = 14  # its first swing, px; each later swing is smaller
CROSSFADE = 0.3  # the longest crossfade into a closing card, s
Spans = Sequence[tuple[float, float]]


class StagingError(SrstudioError, ValueError):
    """A staging does not fit its recording (a style passes its own error class instead)."""


@dataclass(frozen=True)
class Move:
    """A camera move on the shot: a ``crash`` zoom at ``at`` (back out at ``back``), or a ``push`` from ``at`` to
    ``until``; the lens aims at ``x``, ``y``."""

    kind: str
    at: float
    scale: float
    x: float
    y: float
    until: float | None = None
    back: float | None = None


def inside(a: float, b: float, end: float) -> bool:
    """``a`` < ``b``, both finite, inside ``0..end``."""
    return checks.number(a) and checks.number(b) and 0 <= a < b <= end + 1e-6


def check_cover(takes: Sequence[Any], stages: Collection[str], error: type[Exception] = StagingError) -> None:
    """Every take has a stage and every stage a take."""
    ids = {t.id for t in takes}
    if ids != set(stages):
        raise error(
            f"takes without a stage {sorted(ids - set(stages))}, stages without a take {sorted(set(stages) - ids)}"
        )


def check_move(m: Move, end: float, where: str, error: type[Exception] = StagingError) -> None:
    """``m`` is a crash or a push that ends inside the take (``0..end``), at a positive scale and a finite aim."""
    if m.kind not in ("crash", "push"):
        raise error(f"{where}: a move is a crash or a push, not {m.kind!r}")
    stop = m.until if m.kind == "push" else (m.back if m.back is not None else m.at + 0.15)
    if stop is None or not inside(m.at, stop, end):
        raise error(f"{where}: the {m.kind} from {m.at} must end inside the take (0..{end})")
    checks.positive(m.scale, error, f"{where}: the {m.kind}'s scale must be a positive number, got {m.scale!r}")
    if not (checks.number(m.x) and checks.number(m.y)):
        raise error(f"{where}: the {m.kind} aims at ({m.x!r}, {m.y!r}); both must be finite numbers")


def check_spans(
    spans: Spans, end: float, where: str, error: type[Exception] = StagingError, *, ordered: bool = False
) -> None:
    """Each span rises inside the take (``0..end``); ``ordered`` (a shake's spans) also refuses a span that starts
    before the one before it ends."""
    checks.spans(
        spans,
        error,
        lambda s: f"{where}: span {s[0]}..{s[1]} falls outside the take (0..{end})",
        within=end,
        ordered=(lambda s: f"{where}: span {s[0]}..{s[1]} overlaps the one before") if ordered else None,
    )


def shake(cv, group, spans: Spans) -> None:
    """``group`` shaken side to side through each span, settling to rest at its end; every swing falls before
    that end, and spans that overlap or run backwards are a :class:`StagingError`."""
    checks.spans(
        spans,
        StagingError,
        lambda s: f"shake span {s[0]}..{s[1]} must rise from 0",
        ordered=lambda s: f"shake span {s[0]}..{s[1]} overlaps the one before",
    )
    keys: list[tuple[float, float]] = [(0, 0)]
    for a, b in spans:
        n = max(2, int((b - a) / SHAKE_STEP))
        swings = [(round(a + i * SHAKE_STEP, 4), (SHAKE_PX, -SHAKE_PX)[i % 2] * (1 - i / n)) for i in range(n)]
        keys += [(t, v) for t, v in swings if t < round(b, 4)]
        keys.append((round(b, 4), 0))
    cv.keys(group, "x", keys, hold=False)


def _move(cv, group, m: Move) -> None:
    camera.anchor(group, m.x, m.y, place=True)
    if m.kind == "crash":
        camera.crash_zoom(cv, group, m.at, m.scale, back=m.back)
    else:
        until = m.until if m.until is not None else m.at
        camera.push_in(cv, group, scale=[(0, 1.0), (m.at, 1.0), (until, m.scale)])


def rig(cv, parent, move: Move | None, shaking: Spans, *, name: str | None = None):
    """The camera of a shot in ``parent``: a frame group that makes ``move`` holding a group shaken in
    ``shaking``; returns the inner group, which the set, cast and props are drawn into. ``name`` is the frame's id
    (``srstudio.craft`` counts the moves of a group named as the camera); without one it takes a serial id."""
    frame = cv.group(parent, name if name is not None else cv.uid("g"))
    if move is not None:
        _move(cv, frame, move)
    shaken = cv.group(frame, cv.uid("g"))
    if shaking:
        shake(cv, shaken, shaking)
    return shaken


def blackout(cv, parent, spans: Spans):
    """A black rect over the whole frame (and past it, for a shake) shown only in ``spans``; None without spans."""
    if not spans:
        return None
    black = cv.rect(parent, -200, -200, cv.width + 400, cv.height + 400, "#000000")
    cv.gate(black, spans)
    return black


def freeze(shot) -> None:
    """Hold everything drawn in ``shot`` still, as it stands at the shot's start: each ``<animate>`` is replaced by
    its property set to the value it has at second 0 (the first key's value, which a property also holds before its
    first key). A text animator or an expression has no single value to keep, so either is a
    :class:`StagingError`."""
    for node in list(shot.iter()):
        for child in node.elements():
            if child.xml_name in ("textAnimator", "expression"):
                raise StagingError(f"a frozen shot cannot hold the {child.xml_name} on {node.id!r} still")
            if child.xml_name == "animate":
                keys = sorted(child.elements(), key=lambda k: float(k.time))
                at_start = [k for k in keys if float(k.time) <= 0]
                value = (at_start[-1] if at_start else keys[0]).value
                setattr(node, child.property, value)
                node.remove(child)


def crossfades(takes: Sequence[Any], closing: Callable[[str], bool], longest: float = CROSSFADE) -> dict[str, float]:
    """``{take id: seconds}`` for each take that opens a closing card after a take that does not: the crossfade
    into it, at most ``longest`` and half of either shot."""
    return {
        after.id: min(longest, before.duration / 2, after.duration / 2)
        for before, after in zip(takes, takes[1:], strict=False)
        if closing(after.id) and not closing(before.id)
    }


def close(
    ep: Any,
    shots,
    takes: Sequence[Any],
    *,
    fades: Mapping[str, float],
    look: native.CaptionLook,
    pans: Mapping[str, float],
    duck: float,
) -> dict[str, Any]:
    """The end of a reel's build: the crossfades (:func:`crossfades`) between ``shots``, the engine's captions of
    the takes in ``look``, and the mix: each take panned by its actor, the music bed (when the recording has one)
    ducked ``duck`` dB under every line. Returns the caption track and the mix."""
    for before, after in zip(takes, takes[1:], strict=False):
        if after.id in fades:
            native.transition(shots, f"shot-{before.id}", f"shot-{after.id}", "crossfade", duration=fades[after.id])
    captions = ep.native_captions(native.cues_from_takes(takes, look=look), look=look)
    music = ep.t.meta.get("music")
    extra = [("music", music["file"], dict(role="music", gain=str(music["gain_db"])))] if music else []
    mix = ep.audio(
        take=lambda t: dict(pan=pans.get(t.actor, 0.0), fadeIn=".003", fadeOut=".008"),
        extra=extra,
        duck=duck if music else None,
    )
    return {"captions": captions, "mix": mix}
