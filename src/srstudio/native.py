"""Engine-native features the library builds instead of drawing by hand.

- **Caption tracks** (:func:`caption_track`): ``<captions><captionTrack>`` with one ``<cue>`` per line and a
  ``<word>`` per spoken word, so the engine itself sings the words (``karaoke``, ``highlight``, ``pop``...), wraps
  the lines, holds them inside the safe area, burns them into the video and/or writes a WebVTT sidecar
  (``<output stem>.<track>.<language>.vtt``). :func:`cues_from_takes` reads the word timestamps of a shot
  sequence; :func:`cues_from_phrases` the phrases of an interview (no words: the whole cue shows at once).
- **Transitions** (:func:`transition`): ``<transition>`` between two neighbouring shots of a ``<sequence>``
  (``crossfade``, ``whip-pan``, ``push``, ``iris``...), centred on the cut by default.
- **Effects and text animators** live on :class:`~srstudio.canvas.Canvas` (``effect``, ``apply``,
  ``animate_text``); :class:`NativeError` is their error too.

The SDK refuses a preset, type or attribute the schema does not know (:class:`sr_core.scene.SchemaValueError`);
this module refuses what the schema cannot express: cues out of order or overlapping, words outside their cue, a
transition longer than its shots, lines wider than the safe area.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal, get_args

from .errors import SrstudioError
from .fonts import text_width
from .layout import SafeArea
from .timeline import Phrase, Take

Mode = Literal["burn", "sidecar", "both"]


class NativeError(SrstudioError, ValueError):
    """A native feature asked for something the engine cannot show as asked."""


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Cue:
    """One caption on the scene clock; ``words`` (optional) time each word for the word-by-word presets."""

    start: float
    end: float
    text: str
    words: tuple[Word, ...] = ()


@dataclass(frozen=True)
class CaptionLook:
    """How a caption track looks: the engine ``preset``, the face (the house caption look by default: white,
    outlined, the sung word gold) and the line limits the engine wraps by. ``max_chars`` = 24 keeps a mixed-case
    line of DejaVu Sans Bold at 53 px inside the 840 px of the vertical safe area."""

    preset: str = "karaoke"
    size: float = 53
    weight: str = "700"
    color: str = "#FFFFFF"
    active: str = "#F4D492"
    stroke: str = "#121415"
    stroke_width: float = 8
    line_height: float = 1.14
    max_chars: int = 24
    max_lines: int = 2
    max_words: int | None = None
    upper: bool = False
    min_last: int = 1  # the fewest words a cue's last line may hold; more than 1 splits orphaned cues in two
    min_seconds: float = 0.0  # the shortest a cue is shown: held into the silence after it (engine minimum 0.8333)

    def __post_init__(self) -> None:
        for name in ("size", "line_height"):
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 0):
                raise NativeError(f"caption {name} must be a positive number, got {value!r}")
        if not (math.isfinite(self.min_seconds) and self.min_seconds >= 0):
            raise NativeError(f"caption min_seconds must be zero or more seconds, got {self.min_seconds!r}")
        if not (math.isfinite(self.stroke_width) and self.stroke_width >= 0):
            raise NativeError(f"caption stroke_width must be zero or more, got {self.stroke_width!r}")
        for name in ("max_chars", "max_lines", "max_words", "min_last"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                raise NativeError(f"caption {name} must be a whole number of at least 1, got {value!r}")

    @property
    def block(self) -> float:
        """The height of a full caption: ``max_lines`` lines and the outline above and below."""
        return self.max_lines * self.size * self.line_height + 2 * self.stroke_width


CAPTION_LOOK = CaptionLook()  # the house look: white, outlined, the sung word gold


# -- cues -----------------------------------------------------------------------------------------------------------
def cues_from_takes(takes: Iterable[Take], look: CaptionLook | None = None) -> list[Cue]:
    """One cue per spoken take, its words moved onto the scene clock; effect takes are not captioned. With a
    ``look``, a take whose words wrap to more than ``look.max_lines`` is split at words into as few cues as fit,
    each shown from its first word to its last, and then held for ``look.min_seconds`` where the silence after it
    allows: never into the next cue nor past its own take."""
    out: list[tuple[Cue, float]] = []
    for take in takes:
        if take.is_effect or not take.text.strip():
            continue
        words = tuple(Word(w["text"], take.start + w["start"], take.start + w["end"]) for w in take.words)
        start, end = (words[0].start, words[-1].end) if words else (take.start, take.end)
        cue = Cue(start, end, take.text, words)
        out.extend((c, take.end) for c in (_fit(cue, look, take.id, take.end) if look is not None else [cue]))
    if look is None or not look.min_seconds:
        return [c for c, _ in out]
    held = []
    for i, (cue, limit) in enumerate(out):
        cap = min(limit, out[i + 1][0].start) if i + 1 < len(out) else limit
        held.append(replace(cue, end=max(cue.end, min(cue.start + look.min_seconds, cap))))
    return held


def _fit(cue: Cue, look: CaptionLook, where: str, limit: float) -> list[Cue]:
    cues = [cue]
    if len(wrap(cue.text, look.max_chars, look.max_words)) > look.max_lines:
        if not cue.words:
            raise NativeError(f"take {where}: {cue.text!r} needs word timings to be split into cues that fit")
        groups: list[list[Word]] = []
        for word in cue.words:
            if groups and len(wrap(" ".join(w.text for w in [*groups[-1], word]), look.max_chars,
                                   look.max_words)) <= look.max_lines:  # fmt: skip
                groups[-1].append(word)
            else:
                groups.append([word])
        tail = groups[-1]
        if len(groups) > 1 and (len(tail) < look.min_last or limit - tail[0].start < look.min_seconds):
            both = groups[-2] + tail  # the greedy fill left a last cue too small to read: cut the two afresh
            i = _split(both, look, limit)
            if i is not None:
                groups[-2:] = [both[:i], both[i:]]
        cues = [_cue(g) for g in groups]
    if look.min_last > 1:
        cues = [part for c in cues for part in _unorphan(c, look, where, limit)]
    return cues


def _cue(words: Sequence[Word]) -> Cue:
    return Cue(words[0].start, words[-1].end, " ".join(w.text for w in words), tuple(words))


_CLAUSE_END = tuple(".,!?;:…")


def _orphaned(text: str, look: CaptionLook) -> bool:
    lines = wrap(text, look.max_chars, look.max_words)
    return len(lines) > 1 and len(lines[-1].split()) < look.min_last


def _unorphan(cue: Cue, look: CaptionLook, where: str, limit: float) -> list[Cue]:
    """``cue`` as it is, or, when its last line would hold fewer than ``look.min_last`` words, split in two where both
    halves fit without an orphan, the second holds at least ``min_last`` words and each half can be shown for
    ``look.min_seconds`` (the second until ``limit``, its take's end): after a word that ends a clause (``.,!?;:``)
    if one can, else where the halves' lengths balance, the longer half first on a tie. Without such a split the cue
    is kept whole: a lone last word is easier to read than a caption shown too briefly."""
    if not _orphaned(cue.text, look):
        return [cue]
    if not cue.words:
        raise NativeError(f"take {where}: {cue.text!r} needs word timings to be split without an orphan")
    i = _split(cue.words, look, limit)
    return [cue] if i is None else [_cue(cue.words[:i]), _cue(cue.words[i:])]


def _split(words: Sequence[Word], look: CaptionLook, limit: float) -> int | None:
    """Where to cut ``words`` in two (see :func:`_unorphan`), or None when no cut gives two readable halves."""
    best: tuple[tuple[bool, int, int], int] | None = None
    for i in range(1, len(words)):
        halves = [" ".join(w.text for w in part) for part in (words[:i], words[i:])]
        if len(words) - i < look.min_last:  # the second half alone would be the orphan
            continue
        cut = words[i].start
        if cut - words[0].start < look.min_seconds or limit - cut < look.min_seconds:
            continue
        if any(len(wrap(t, look.max_chars, look.max_words)) > look.max_lines or _orphaned(t, look) for t in halves):
            continue
        score = (not halves[0].endswith(_CLAUSE_END), max(len(t) for t in halves), -len(halves[0]))
        if best is None or score < best[0]:
            best = (score, i)
    return None if best is None else best[1]


def cues_from_phrases(phrases: Iterable[Phrase], lead: float = 0.0) -> list[Cue]:
    """One cue per phrase, its caption on one line (the engine wraps it), shown ``lead`` seconds early."""
    return [Cue(max(0.0, p.start - lead), p.end, " ".join(p.caption.split())) for p in phrases]


def _check_cues(cues: Sequence[Cue]) -> None:
    if not cues:
        raise NativeError("a caption track needs cues, got no cues")
    last = None
    for cue in sorted(cues, key=lambda c: c.start):
        label = f"cue {cue.text!r} at {cue.start}"
        if not (math.isfinite(cue.start) and math.isfinite(cue.end)):
            raise NativeError(f"{label}: times must be finite")
        if cue.start < 0:
            raise NativeError(f"{label}: starts before 0")
        if cue.end <= cue.start:
            raise NativeError(f"{label}: ends at {cue.end}, not after it starts")
        if not cue.text.strip():
            raise NativeError(f"{label}: has no text")
        if last is not None and cue.start < last.end:
            raise NativeError(f"{label}: overlaps cue {last.text!r} ending at {last.end}")
        last = cue
        before = cue.start
        for w in cue.words:
            if not w.text.strip():
                raise NativeError(f"{label}: a word has no text")
            if not (math.isfinite(w.start) and math.isfinite(w.end)) or w.end <= w.start:
                raise NativeError(f"{label}: word {w.text!r} ends at {w.end}, not after it starts")
            if w.start < cue.start or w.end > cue.end:
                raise NativeError(f"{label}: word {w.text!r} ({w.start}-{w.end}) is outside the cue")
            if w.start < before:
                raise NativeError(f"{label}: word {w.text!r} is out of order")
            before = w.end


def wrap(text: str, max_chars: int, max_words: int | None = None) -> list[str]:
    """Greedy lines of at most ``max_chars`` characters and ``max_words`` words, as the engine breaks a cue."""
    lines: list[list[str]] = []
    for word in text.split():
        line = lines[-1] if lines else None
        if line and len(" ".join([*line, word])) <= max_chars and (max_words is None or len(line) < max_words):
            line.append(word)
        else:
            lines.append([word])
    return [" ".join(line) for line in lines]


def _check_fit(cues: Sequence[Cue], look: CaptionLook, font_data: bytes, room: float) -> None:
    for cue in cues:
        text = cue.text.upper() if look.upper else cue.text
        lines = wrap(text, look.max_chars, look.max_words)
        if len(lines) > look.max_lines:
            raise NativeError(f"cue {cue.text!r} wraps to {len(lines)} lines, more than {look.max_lines}: split it")
        for line in lines:
            wide = text_width(font_data, line, look.size) + 2 * look.stroke_width
            if wide > room:
                raise NativeError(f"cue {cue.text!r}: the line {line!r} is {wide:.0f} px, wider than {room:.0f} px")


# -- caption tracks -------------------------------------------------------------------------------------------------
def _percent(value: float) -> str:
    return f"{math.floor(value * 10000) / 100:g}%"


def caption_track(
    scene: Any,
    cues: Sequence[Cue],
    *,
    font_asset: str | None,
    safe_area: SafeArea | None,
    width: int,
    height: int,
    look: CaptionLook = CAPTION_LOOK,
    output: Any = None,
    mode: Mode = "burn",
    id: str = "captions",
    language: str = "en-US",
    font_data: bytes | None = None,
):
    """Add the caption track ``id`` showing ``cues`` and return it.

    With a ``safe_area`` the track is centred on it and its last line sits on its bottom edge; without one it keeps
    the engine's placement. ``mode`` ``burn`` draws it into ``output``, ``sidecar`` writes it beside the video,
    ``both`` does both; either needs the ``output``. ``font_data`` (the bytes of the caption font) measures every
    wrapped line against the room it has. Nothing is added when a check fails."""
    if mode not in get_args(Mode):
        raise NativeError(f"caption mode must be one of {get_args(Mode)}, not {mode!r}")
    if font_asset is None:
        raise NativeError("a caption track needs a font asset; set EpisodeSpec.font")
    if output is None and mode != "burn":
        raise NativeError(f"a {mode} caption track needs the output it is written beside")
    _check_cues(cues)
    place: dict[str, str] = {}
    room = width * 0.85
    if safe_area is not None:
        region = safe_area.region(width, height)
        room = region.x1 - region.x0
        if look.block > region.y1 - region.y0:
            raise NativeError(f"the caption block ({look.block:.0f} px) is taller than the safe area")
        place = dict(
            x=_percent((region.x0 + region.x1) / 2 / width),
            y=_percent((region.y1 - look.block) / height),
            width=_percent(room / width),
            safeArea=safe_area.id,
        )
    if font_data is not None:
        _check_fit(cues, look, font_data, room)

    track_kw: dict[str, Any] = dict(
        id=id,
        language=language,
        preset=look.preset,
        mode=mode,
        style=f"{id}-text",
        activeStyle=f"{id}-active",
        maxCharsPerLine=look.max_chars,
        maxLines=look.max_lines,
        **place,
    )
    if look.max_words is not None:
        track_kw["maxWordsPerLine"] = look.max_words
    captions = scene.find("captions")
    fresh = captions is None
    if captions is None:
        captions = scene.add_captions()
    try:
        track = captions.add_captionTrack(**track_kw)
    except Exception:  # a preset the schema does not know: leave the document as it was
        if fresh:
            scene.remove(captions)
        raise
    styles = scene.find("styles") or scene.add_styles()
    base_kw: dict[str, Any] = dict(
        fontAsset=font_asset,
        size=look.size,
        weight=look.weight,
        color=look.color,
        lineHeight=look.line_height,
        strokeColor=look.stroke,
        strokeWidth=look.stroke_width,
        strokePosition="outside",
    )
    if look.upper:
        base_kw["textTransform"] = "uppercase"
    styles.add_textStyle(id=f"{id}-text", **base_kw)
    styles.add_textStyle(id=f"{id}-active", basedOn=f"{id}-text", color=look.active)
    for cue in sorted(cues, key=lambda c: c.start):
        element = track.add_cue(start=round(cue.start, 6), end=round(cue.end, 6), text=cue.text)
        for w in cue.words:
            element.add_word(start=round(w.start, 6), end=round(w.end, 6), text=w.text)
    if output is not None and mode in ("burn", "both"):
        output.burnCaptions = id
    if output is not None and mode in ("sidecar", "both"):
        output.captions = id
    return track


# -- transitions ----------------------------------------------------------------------------------------------------
def _spans(sequence: Any) -> dict[str, tuple[int, float, float]]:
    """Each shot of ``sequence``: its position and its span on the sequence's clock. A shot's ``end`` is its length
    on its own clock (the engine plays each child for its ``end``, then the next), so a shot starts where the one
    before it ends."""
    out, start = {}, 0.0
    shots = [c for c in sequence.elements() if c.xml_name != "transition"]
    for k, shot in enumerate(shots):
        length = float(shot.end) - float(shot.start or 0) if shot.end is not None else math.inf
        if shot.id is not None:
            out[shot.id] = (k, start, start + length)
        start += length
    return out


def transition(sequence: Any, from_: str, to: str, type: str = "crossfade", duration: float = 0.3, **kw: Any):
    """A ``type`` transition of ``duration`` seconds from shot ``from_`` to the shot ``to`` that follows it,
    centred on the cut (``alignment``, ``direction``, ``color``... pass through)."""
    spans = _spans(sequence)
    for shot in (from_, to):
        if shot not in spans:
            raise NativeError(f"no shot {shot!r} in sequence {sequence.id!r}")
    (i, a0, a1), (j, b0, b1) = spans[from_], spans[to]
    if j != i + 1:
        raise NativeError(f"shot {to!r} does not follow {from_!r} in sequence {sequence.id!r}")
    if not (math.isfinite(duration) and duration > 0):
        raise NativeError(f"a transition duration must be positive, got {duration!r}")
    if duration > min(a1 - a0, b1 - b0):
        raise NativeError(f"a {duration} s transition is longer than shot {from_!r} or {to!r}")
    element = sequence.add_transition(type=type, from_=from_, to=to, duration=duration, **kw)
    sequence.remove(element)  # written between the two shots it joins
    nodes = list(sequence.nodes)
    sequence.nodes.insert(nodes.index(next(c for c in sequence.elements() if c.id == to)), element)
    return element
