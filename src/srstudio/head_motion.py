"""Organic head motion as data (ADR 0050): what a drawn head does while it listens, speaks and sits still, as sparse
keys for the engine's own curves, deterministic and bounded.

:func:`plan` turns a :class:`HeadStyle` and the :class:`Speech` of a shot into a :class:`HeadPlan`, one
:class:`Channel` per thing that moves and a track of where the eyes look:

* **Springs.** A nod, a glance and a lean are targets on spring keys the engine evaluates (``spring`` with
  ``carry="true"``), so the motion lags, overshoots and settles without a frame being baked here. A :class:`Spring`
  is named by frequency and damping ratio.
* **Speech.** A nod falls on about four in five accents (:func:`accents`: content words whose stressed syllable, from
  the CMU Pronouncing Dictionary, stands above the phrase's loudness), spans two to four phones and leads its
  syllable; a phrase after a pause opens with a dip; a character repeats one movement type; an intensifier earns a
  bigger nod. The counts follow Graf, Cosatto, Strom and Huang, *Visual Prosody* (2002).
* **Idle.** Two octaves of hashed 1-D gradient noise, ducked while speaking, and a breath taken in the pauses and let
  out across the phrases, or an uneven slow cycle in silence.
* **Glances.** The eyes jump on hold keys; the head follows late through its spring and comes back.
* **Listening.** What another character says is ``heard``: the listener's eyes stay on them, its idle quiets, and it
  gives a small nod of its own signature at the end of their phrases (:func:`listening`).

No draw comes from a global generator or the clock: :func:`hash_unit` hashes the seed, a channel name and an ordinal,
so one channel never shifts another. The head-drawing side is :mod:`srstudio.toon_head`.
"""

from __future__ import annotations

import gzip
import hashlib
import math
import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import TypeAlias

from . import checks, soundtrack
from .errors import SrstudioError
from .voice import Alignment

__all__ = [
    "AVERT_BACK",
    "CHANNELS",
    "DUCK",
    "GAZES",
    "INTENSIFIER_GAIN",
    "LISTEN_SHARE",
    "LOUD_RATE",
    "Accent",
    "Channel",
    "HeadMotionError",
    "HeadPlan",
    "HeadStyle",
    "Nod",
    "Speech",
    "Spring",
    "Word",
    "accents",
    "dips",
    "fbm",
    "hash_unit",
    "limit",
    "listening",
    "nods",
    "noise",
    "plan",
    "speech_of",
    "stress",
    "stressed_at",
    "words_of",
]

Key: TypeAlias = tuple[float, float]

LOUD_RATE = 100  # loudness samples a second
PAUSE = 0.25  # the silence, in seconds, that starts a new breath
DUCK = 0.4  # how much of the idle wander is left while speaking
INTENSIFIER_GAIN = 1.5  # how much bigger a nod on an intensifier is
LISTEN_SHARE = 0.35  # how big a listener's nod is, as a share of a full nod
LISTEN_LAG = 0.15  # how long after the other's accent the listener's nod starts
AVERT_BACK = 0.1  # how long before a line's first word the eyes are back
AVERT = 0.7  # how long before a line's first word they leave
ANTICIPATE = 0.08  # seconds of the small opposite move before a nod
NOD_SPAN = (0.12, 0.4)  # the shortest and longest nod, in seconds
PHONES = 3  # the letters of the stressed syllable a nod spans: Graf's two to four phones
GAZES = {"ahead": (0.0, 0.0), "left": (-0.42, 0.04), "right": (0.42, 0.04), "up": (0.0, -0.3)}  # in eye radii
LOOK_AWAY = (("left", 0.4), ("right", 0.8), ("up", 1.0))  # the share of glances each way, cumulative
CHANNELS = ("lean", "turn", "nod", "roll", "face_x", "idle_roll", "idle_y", "breath")
_ROOM = 1.25  # what a spring may add over its largest target, carried momentum included

_VOWELS = re.compile(r"[aeiouy]+")
_WORD = re.compile(r"[\w'’-]")
_STOPS = frozenset(".,;:!?…—")
_FUNCTION = frozenset(
    """a about after all also am an and any are as at be because been before but by can could did do does down each else
    even ever every for from had has have he her here hers him his how i if in into is it its just let me might more
    most much must my no nor not now of off on once one only onto or other our out over own she should since so some
    such than that the their them then there these they this those to too under until up us very was we were what
    when where which while who whom whose why will with would yet you your""".split()
)
_INTENSIFIERS = frozenset(
    """absolutely completely definitely entirely extremely forever literally never really seriously so totally truly
    utterly very""".split()
)


class HeadMotionError(SrstudioError, ValueError):
    """Head motion was asked for something it cannot do; the message names what."""


def _finite(*values: float) -> bool:
    return all(checks.number(v) for v in values)


# -- noise -------------------------------------------------------------------------------------------------------------
def hash_unit(seed: int, channel: str, index: int) -> float:
    """A value in [0, 1) from the seed, a channel name and an ordinal: the same on every machine and Python."""
    digest = hashlib.blake2b(f"{seed}:{channel}:{index}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def noise(x: float, seed: int, channel: str) -> float:
    """1-D gradient noise in [-1, 1], zero at every integer ``x``."""
    i = math.floor(x)
    u = x - i
    fade = u * u * u * (u * (6.0 * u - 15.0) + 10.0)
    near = (2.0 * hash_unit(seed, channel, i) - 1.0) * u
    far = (2.0 * hash_unit(seed, channel, i + 1) - 1.0) * (u - 1.0)
    return 2.0 * (near + (far - near) * fade)


def fbm(t: float, hz: float, seed: int, channel: str, octaves: int = 2) -> float:
    """``octaves`` of :func:`noise` from ``hz`` up, each an octave higher and half as strong, in [-1, 1]."""
    if not _finite(t, hz):
        raise HeadMotionError(f"noise needs finite numbers, got t={t!r}, hz={hz!r}")
    total = sum(0.5**k * noise(2**k * hz * t, seed, f"{channel}/{k}") for k in range(octaves))
    return total / sum(0.5**k for k in range(octaves))


# -- springs and channels ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Spring:
    """A spring by its feel: ``frequency`` in Hz, ``damping`` as a ratio (under 1 overshoots, 1 settles without) and
    ``anticipation``, the share of a move taken the other way first."""

    frequency: float
    damping: float
    anticipation: float = 0.0

    def __post_init__(self) -> None:
        if not (_finite(self.frequency, self.damping, self.anticipation)):
            raise HeadMotionError(f"a spring needs finite numbers, got {self!r}")
        if self.frequency <= 0 or not 0 < self.damping <= 2 or not 0 <= self.anticipation <= 0.5:
            raise HeadMotionError(f"a spring has frequency > 0, damping 0..2 and anticipation 0..0.5, got {self!r}")

    @property
    def stiffness(self) -> float:
        return (2.0 * math.pi * self.frequency) ** 2

    @property
    def friction(self) -> float:
        return 2.0 * self.damping * 2.0 * math.pi * self.frequency

    def attributes(self) -> dict[str, str]:
        """The key attributes of the engine's ``spring`` curve, at a mass of 1."""
        return {"stiffness": f"{self.stiffness:.4f}", "damping": f"{self.friction:.4f}", "mass": "1"}


@dataclass(frozen=True)
class Channel:
    """One moving value: ``(project second, value)`` keys on a :class:`Spring`, or on an engine ``curve``."""

    keys: tuple[Key, ...] = ()
    spring: Spring | None = None
    curve: str = "linear"

    def __post_init__(self) -> None:
        if any(not _finite(t, v) for t, v in self.keys):
            raise HeadMotionError(f"a channel's keys are finite, got {self.keys!r}")
        if any(b[0] <= a[0] for a, b in zip(self.keys, self.keys[1:], strict=False)):
            raise HeadMotionError(f"a channel's key times rise, got {self.keys!r}")

    def during(self, start: float, end: float) -> Channel:
        """The keys a shot from ``start`` to ``end`` plays: those inside it and one either side, so each shot of a
        sketch carries its own stretch of the timeline and a value is the same on both sides of a cut."""
        before = [key for key in self.keys if key[0] <= start][-1:]
        inside = [key for key in self.keys if start < key[0] < end]
        after = [key for key in self.keys if key[0] >= end][:1]
        return replace(self, keys=(*before, *inside, *after))


@dataclass(frozen=True)
class HeadStyle:
    """How one character moves its head (reference pixels and degrees). ``signature`` is its one nod: ``^`` a swing and
    back, ``~`` the same with a swing past rest on the way back, ``/`` a slow shift that drifts back."""

    seed: int
    signature: str
    nod_px: float
    nod_roll: float
    head: Spring
    settle: Spring
    body: Spring
    nod_share: float = 0.8
    min_gap: float = 0.45
    lead: float = 0.06
    accent_db: float = 1.0
    loud_range: float = 12.0
    lean: float = 0.6
    follow: float = 0.6
    idle_roll: float = 1.2
    idle_px: float = 0.8
    idle_hz: float = 0.15
    breath_period: float = 5.0
    breath_px: float = 3.0
    breath_scale: float = 0.012
    glance_every: float = 4.0
    glance_hold: float = 1.0
    glance_turn: float = 1.5
    glance_face: float = 6.0
    avert: float = 0.5

    def __post_init__(self) -> None:
        if self.signature not in ("^", "~", "/"):
            raise HeadMotionError(f"signature is ^, ~ or /, got {self.signature!r}")
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, float | int) and not checks.number(value):
                raise HeadMotionError(f"{field.name} must be finite, got {value!r}")
        for name in ("nod_px", "idle_hz", "breath_period", "glance_every", "glance_hold", "loud_range"):
            if getattr(self, name) <= 0:
                raise HeadMotionError(f"{name} must be positive, got {getattr(self, name)!r}")
        for name in ("nod_roll", "min_gap", "lead", "accent_db", "lean", "idle_roll", "idle_px", "breath_px"):
            if getattr(self, name) < 0:
                raise HeadMotionError(f"{name} must not be negative, got {getattr(self, name)!r}")
        for name in ("glance_turn", "glance_face"):
            if getattr(self, name) < 0:
                raise HeadMotionError(f"{name} must not be negative, got {getattr(self, name)!r}")
        for name in ("nod_share", "follow", "avert"):
            if not 0 <= getattr(self, name) <= 1:
                raise HeadMotionError(f"{name} is a share, 0 to 1, got {getattr(self, name)!r}")
        if not 0 <= self.breath_scale < 0.1:
            raise HeadMotionError(f"breath_scale is under a tenth, got {self.breath_scale!r}")


def limit(style: HeadStyle, name: str) -> float:
    """The most a channel of ``style`` may reach, overshoot and carried momentum included."""
    lean = style.lean * _ROOM
    return {
        "lean": lean,
        "turn": (style.glance_turn + style.follow * style.lean) * _ROOM,
        "nod": style.nod_px * INTENSIFIER_GAIN * _ROOM,
        "roll": style.nod_roll * INTENSIFIER_GAIN * _ROOM,
        "face_x": style.glance_face * _ROOM,
        "idle_roll": style.idle_roll,
        "idle_y": style.idle_px,
        "breath": 1.0,
    }[name]


# -- words -------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Word:
    """A spoken word in project seconds: its letters, each letter's start and end, and whether punctuation follows."""

    text: str
    start: float
    end: float
    chars: tuple[tuple[float, float], ...]
    stop: bool

    def __post_init__(self) -> None:
        if not self.text or len(self.chars) != len(self.text):
            raise HeadMotionError(f"a word has one time span per letter, got {self.text!r} and {self.chars!r}")
        if not _finite(self.start, self.end) or self.end < self.start:
            raise HeadMotionError(f"{self.text!r}: a word ends after it starts, got {self.start!r}..{self.end!r}")


def words_of(alignment: Alignment, at: float) -> tuple[Word, ...]:
    """The words of a take's character timestamps, placed from project second ``at``."""
    if not (_finite(at) and at >= 0):
        raise HeadMotionError(f"a take is placed at a second >= 0, got {at!r}")
    words: list[Word] = []
    current: list[tuple[str, float, float]] = []

    def close(stop: bool) -> None:
        if current:
            spans = tuple((round(at + a, 6), round(at + b, 6)) for _, a, b in current)
            text = "".join(c for c, _, _ in current)
            words.append(Word(text, spans[0][0], spans[-1][1], spans, stop))
            current.clear()

    last = 0.0
    for c, a, b in zip(alignment.characters, alignment.starts, alignment.ends, strict=True):
        if a < last or b < a:
            raise HeadMotionError(f"a take's character times rise, got {c!r} at {a!r}..{b!r} after {last!r}")
        last = a
        if _WORD.match(c):
            current.append((c, a, b))
        else:
            stop = c in _STOPS
            if stop and not current and words:
                previous = words[-1]
                words[-1] = Word(previous.text, previous.start, previous.end, previous.chars, True)
            close(stop)
    close(True)
    return tuple(words)


@lru_cache(maxsize=1)
def _lexicon() -> dict[str, str]:
    """Each word's stress digits, one per syllable (``assets/stress``, from the CMU Pronouncing Dictionary)."""
    path = resources.files("srstudio").joinpath("assets/stress/cmudict-stress.txt.gz")
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    return dict(line.split("\t") for line in text.splitlines())


def stress(word: str) -> tuple[int, int]:
    """The stressed syllable's index and the syllable count of ``word``: from the dictionary, or for a word it lacks,
    the first of its vowel groups."""
    key = word.lower().replace("’", "'")
    digits = _lexicon().get(key, "")
    if digits:
        mark = "1" if "1" in digits else "2" if "2" in digits else digits[0]
        return digits.index(mark), len(digits)
    return 0, max(1, len(_VOWELS.findall(key)))


def stressed_at(word: Word) -> tuple[float, float]:
    """When the stressed syllable of ``word`` starts and how long :data:`PHONES` letters from it last. Spelling and
    syllables rarely line up one to one: a word whose vowel groups do not match its syllables is cut in proportion."""
    index, count = stress(word.text)
    groups = [m.start() for m in _VOWELS.finditer(word.text.lower())]
    letter = groups[index] if len(groups) == count else index * len(word.text) // count
    last = min(letter + PHONES - 1, len(word.text) - 1)
    return word.chars[letter][0], round(word.chars[last][1] - word.chars[letter][0], 6)


# -- speech ------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Speech:
    """One take in the shot: where it starts, its words and its loudness in dB, :data:`LOUD_RATE` samples a second."""

    at: float
    words: tuple[Word, ...]
    levels: tuple[float, ...]

    def __post_init__(self) -> None:
        if not (_finite(self.at) and self.at >= 0):
            raise HeadMotionError(f"speech starts at a second >= 0, got {self.at!r}")
        if not self.levels or not _finite(*self.levels):
            raise HeadMotionError("speech needs finite loudness samples")
        if any(b.start < a.start for a, b in zip(self.words, self.words[1:], strict=False)):
            raise HeadMotionError("speech's words must be in time order")

    def level(self, t: float) -> float:
        """The loudness at project second ``t``, the nearest sample past either end."""
        return self.levels[min(len(self.levels) - 1, max(0, int((t - self.at) * LOUD_RATE)))]

    def peak(self, t0: float, t1: float) -> float:
        count = max(1, int((t1 - t0) * LOUD_RATE))
        return max(self.level(t0 + k / LOUD_RATE) for k in range(count))


def speech_of(alignment: Alignment, at: float, path: str | Path) -> Speech:
    """A take as :class:`Speech`: its words and the loudness of its audio file, read once."""
    track = soundtrack.Soundtrack(path)
    window = 2.0 / LOUD_RATE
    levels = (
        20.0 * math.log10(max(track.rms(k / LOUD_RATE, k / LOUD_RATE + window), 1e-5))
        for k in range(int(track.duration * LOUD_RATE))
    )
    return Speech(at, words_of(alignment, at), tuple(levels))


def _phrases(speech: Speech) -> list[list[Word]]:
    out: list[list[Word]] = []
    for word in speech.words:
        if out and word.start - out[-1][-1].end < PAUSE and not out[-1][-1].stop:
            out[-1].append(word)
        else:
            out.append([word])
    return out


def _breaths(speech: Speech) -> list[tuple[float, float]]:
    """The runs of speech with no pause inside, ``(start, end)``."""
    out: list[tuple[float, float]] = []
    for word in speech.words:
        if out and word.start - out[-1][1] < PAUSE:
            out[-1] = (out[-1][0], word.end)
        else:
            out.append((word.start, word.end))
    return out


@dataclass(frozen=True)
class Accent:
    """A stressed word: when its syllable starts, how long it lasts and how far it stands above the phrase, in dB.
    ``nuclear`` marks the last accent of a phrase, the one English puts the news on."""

    word: Word
    at: float
    span: float
    over: float
    nuclear: bool = False


def _content(word: Word) -> bool:
    key = word.text.lower()
    return key not in _FUNCTION or key in _INTENSIFIERS


def accents(speech: Speech, style: HeadStyle) -> list[Accent]:
    """The content words of each phrase whose stressed syllable stands :attr:`HeadStyle.accent_db` over the phrase's
    median loudness, and always its loudest one and its last one, so a flat read still lands and a line trailing off
    into its point keeps it."""
    out: list[Accent] = []
    for phrase in _phrases(speech):
        low, high = phrase[0].start, phrase[-1].end
        steps = range(max(1, int((high - low) * LOUD_RATE)))
        median = statistics.median(speech.level(low + k / LOUD_RATE) for k in steps)
        found = []
        for word in phrase:
            if _content(word):
                at, span = stressed_at(word)
                found.append(Accent(word, at, span, speech.peak(at, at + span) - median))
        if found:
            top = max(found, key=lambda a: a.over)
            kept = [a for a in found if a.over >= style.accent_db or a is top or a is found[-1]]
            out += [*kept[:-1], replace(kept[-1], nuclear=True)]
    return out


@dataclass(frozen=True)
class Nod:
    """A head movement on an accent: its type, when it starts, how long it swings and how far, in reference pixels."""

    word: str
    kind: str
    at: float
    span: float
    amplitude: float


def nods(speech: Speech, style: HeadStyle, index: int = 0) -> list[Nod]:
    """The nods of one take: about :attr:`HeadStyle.nod_share` of its accents, nuclear ones always and the others
    drawn to make up the share, never closer than :attr:`HeadStyle.min_gap`, each :attr:`HeadStyle.lead` ahead of its
    syllable, stronger the louder the accent."""
    found = accents(speech, style)
    if not style.nod_share:
        return []
    nuclear = sum(a.nuclear for a in found)
    others = (style.nod_share * len(found) - nuclear) / max(1, len(found) - nuclear)
    out: list[Nod] = []
    for k, accent in enumerate(found):
        if not accent.nuclear and hash_unit(style.seed, f"accent/{index}", k) >= others:
            continue
        at = max(0.0, accent.at - style.lead)
        if out and at - out[-1].at < style.min_gap:
            if not accent.nuclear:
                continue
            out.pop()
        strength = min(1.0, max(0.5, accent.over / style.loud_range))
        gain = INTENSIFIER_GAIN if accent.word.text.lower() in _INTENSIFIERS else 1.0
        span = min(NOD_SPAN[1], max(NOD_SPAN[0], accent.span))
        out.append(Nod(accent.word.text, style.signature, round(at, 6), span, style.nod_px * strength * gain))
    return out


def listening(speech: Speech, style: HeadStyle, index: int, busy: Sequence[tuple[float, float]] = ()) -> list[Nod]:
    """The nods of a character hearing ``speech``: about :attr:`HeadStyle.nod_share` of the phrase ends, each
    :data:`LISTEN_SHARE` of a full nod in its own signature, just after the accent the news is on; none that would
    fall while it is ``busy`` speaking itself."""
    out: list[Nod] = []
    for k, accent in enumerate(a for a in accents(speech, style) if a.nuclear):
        at = round(accent.at + accent.span + LISTEN_LAG, 6)
        kept = hash_unit(style.seed, f"listen/{index}", k) < style.nod_share
        talking = any(a - style.min_gap <= at <= b + style.min_gap for a, b in busy)
        if kept and not talking and (not out or at - out[-1].at >= style.min_gap):
            span = min(NOD_SPAN[1], max(NOD_SPAN[0], accent.span))
            out.append(Nod(accent.word.text, style.signature, at, span, style.nod_px * LISTEN_SHARE))
    return out


def dips(speech: Speech) -> list[float]:
    """The word starts that follow a pause, where the head dips before it rises into the phrase."""
    return [start for start, _ in _breaths(speech)]


# -- the keys ----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class _Move:
    at: float
    shape: tuple[Key, ...]  # (seconds after ``at``, share of ``amplitude``)
    amplitude: float


_DIP = ((0.0, 0.0), (0.15, 1.0), (0.36, -0.7), (0.8, 0.0))
_DIP_LEAD = 0.2  # how long before its phrase a dip starts
_DIP_SHARE = 0.2  # a dip's depth, as a share of a full nod


def _shape(kind: str, span: float) -> tuple[Key, ...]:
    if kind == "^":
        return ((0.0, 0.0), (span * 0.5, 1.0), (span + 0.35, 0.0))
    if kind == "~":
        return ((0.0, 0.0), (span * 0.5, 1.0), (span, -0.4), (span + 0.45, 0.0))
    return ((0.0, 0.0), (span + 0.1, 1.0), (span + 0.35, 0.9), (span + 1.3, 0.0))


def _chain(moves: Sequence[_Move], spring: Spring, duration: float) -> tuple[Key, ...]:
    """The keys of ``moves`` in time order: each starts from rest, after a small opposite move when the spring
    anticipates, unless the one before was cut short by it, when it runs straight on."""
    keys: list[Key] = [(0.0, 0.0)]
    ordered = sorted(moves, key=lambda m: m.at)
    for i, move in enumerate(ordered):
        cut = ordered[i + 1].at - 0.02 if i + 1 < len(ordered) else math.inf
        points = [(move.at + dt, share * move.amplitude) for dt, share in move.shape]
        lead = ANTICIPATE if spring.anticipation else 0.0
        if keys[-1][1] != 0.0:
            points = [(t + lead, v) for t, v in points[1:]]
        elif lead:
            points = [
                points[0],
                (move.at + lead, -spring.anticipation * move.amplitude),
                *[(t + lead, v) for t, v in points[1:]],
            ]
        for t, v in points:
            if keys[-1][0] < t < cut:
                keys.append((round(t, 6), round(v, 4)))
    return _close(keys, duration)


def _close(keys: Sequence[Key], duration: float) -> tuple[Key, ...]:
    """``keys`` before the end of the shot, coming to rest by the end."""
    kept = [key for key in keys if key[0] < duration]
    if kept[-1][1] != 0.0:
        kept.append((round(duration, 6), 0.0))
    return tuple(kept)


def _trapezoids(spans: Sequence[tuple[float, float, float, float, float]], duration: float) -> tuple[Key, ...]:
    """The sum of ``(on, up, off, down, value)`` ramps as keys at their corners."""
    corners = {0.0}
    for on, up, off, down, _ in spans:
        corners |= {round(on, 6), round(on + up, 6), round(off, 6), round(off + down, 6)}

    def at(t: float) -> float:
        total = 0.0
        for on, up, off, down, value in spans:
            if on < t < on + up:
                total += value * (t - on) / up
            elif on + up <= t <= off:
                total += value
            elif off < t < off + down:
                total += value * (off + down - t) / down
        return total

    return _close([(t, round(at(t), 4)) for t in sorted(corners)], duration)


def _noise_keys(
    style: HeadStyle, name: str, amount: float, spans: Sequence[tuple[float, float]], duration: float
) -> tuple[Key, ...]:
    step = 1.0 / (8.0 * style.idle_hz)
    times = [k * step for k in range(int(duration / step) + 1)]
    if times[-1] < duration:
        times.append(duration)
    keys = []
    for t in times:
        duck = DUCK if any(a - 0.2 <= t <= b + 0.2 for a, b in spans) else 1.0
        keys.append((round(t, 6), round(amount * duck * fbm(t, style.idle_hz, style.seed, name), 4)))
    return tuple(keys)


def _breath_keys(style: HeadStyle, spans: Sequence[tuple[float, float]], duration: float) -> tuple[Key, ...]:
    """In before each run of speech and out across it; in silence an uneven cycle, in quicker than out, and a shot ends
    wherever its last breath has got to."""
    keys: list[Key] = [(0.0, 0.0)]
    period = style.breath_period
    inhale = period * 0.4
    k = 0

    def length() -> float:
        return period * (0.85 + 0.3 * hash_unit(style.seed, "breath", k))

    def quiet(until: float) -> None:
        nonlocal k
        while True:
            span = length()
            at = keys[-1][0]
            if at + span > until:
                return
            k += 1
            keys.append((round(at + span * 0.4, 6), 1.0))
            keys.append((round(at + span, 6), 0.0))

    for start, end in spans:
        before = max(keys[-1][0], start - min(inhale, 0.6))
        quiet(before)
        at = keys[-1][0]
        if start > at:
            keys.append((round(start, 6), 1.0))
        if end > keys[-1][0]:
            keys.append((round(end, 6), 0.0))
    quiet(duration)
    span, at = length(), keys[-1][0]
    top = at + span * 0.4
    if top < duration:
        keys.append((round(top, 6), 1.0))
        keys.append((round(duration, 6), round(1.0 - (duration - top) / (span * 0.6), 4)))
    elif at < duration:
        keys.append((round(duration, 6), round((duration - at) / (span * 0.4), 4)))
    return tuple(keys)


def _gaze(
    style: HeadStyle, speeches: Sequence[Speech], spans: Sequence[tuple[float, float]], duration: float
) -> list[tuple[float, float, str]]:
    """Where the eyes look away, ``(on, off, name)``: at a line's start, sometimes, and every few seconds of silence,
    never while a word is being said."""
    out: list[tuple[float, float, str]] = []

    def way(k: int) -> str:
        draw = hash_unit(style.seed, "gaze", k)
        return next(name for name, share in LOOK_AWAY if draw < share)

    def free(a: float, b: float) -> bool:
        return all(b + 0.4 < s or a - 0.4 > e for s, e in spans) and all(b < on or a > off for on, off, _ in out)

    for i, speech in enumerate(speeches):
        first = speech.words[0].start if speech.words else None
        if first is None or first - AVERT < 0 or hash_unit(style.seed, "avert", i) >= style.avert:
            continue
        before = [e for s, e in spans if e < first]
        if not before or first - AVERT > before[-1] + 0.4:
            out.append((round(first - AVERT, 6), round(first - AVERT_BACK, 6), way(i)))
    t, k = 0.0, 0
    while True:
        t += style.glance_every * (0.7 + 0.6 * hash_unit(style.seed, "glance", k))
        hold = style.glance_hold * (0.8 + 0.4 * hash_unit(style.seed, "hold", k))
        k += 1
        if t + hold + 1.0 >= duration:
            break
        if free(t, t + hold):
            out.append((round(t, 6), round(t + hold, 6), way(100 + k)))
    return sorted(out)


@dataclass(frozen=True)
class HeadPlan:
    """Everything a head does in a shot. ``lean`` turns the body about the seat, ``turn`` and ``roll`` the head about
    the neck (degrees), ``nod`` moves it down and ``face_x`` slides the face across it (reference pixels),
    ``idle_roll`` and ``idle_y`` wander, ``breath`` goes 0 to 1, and ``gaze`` is ``(project second, name in GAZES)``
    hold states."""

    lean: Channel = Channel()
    turn: Channel = Channel()
    nod: Channel = Channel()
    roll: Channel = Channel()
    face_x: Channel = Channel()
    idle_roll: Channel = Channel()
    idle_y: Channel = Channel()
    breath: Channel = Channel()
    gaze: tuple[tuple[float, str], ...] = ()

    @classmethod
    def still(cls) -> HeadPlan:
        """A head that does not move: the same drawing with no keys."""
        return cls()

    def during(self, start: float, end: float) -> HeadPlan:
        """This plan's keys for a shot from ``start`` to ``end`` (:meth:`Channel.during`); the gaze stays whole, its
        runs cut by :func:`srstudio.toon_head.gaze_states`."""
        return replace(self, **{name: getattr(self, name).during(start, end) for name in CHANNELS})


def _check(style: HeadStyle, speeches: Sequence[Speech], duration: float) -> None:
    if not (_finite(duration) and duration > 0):
        raise HeadMotionError(f"a shot lasts a positive number of seconds, got {duration!r}")
    last = 0.0
    for speech in speeches:
        if speech.at < last:
            raise HeadMotionError(f"speech is in time order and does not overlap: {speech.at!r} after {last!r}")
        if speech.words:
            last = speech.words[-1].end
            if last > duration:
                raise HeadMotionError(f"speech runs to {last!r}, past the shot's {duration!r} s")


def plan(style: HeadStyle, speeches: Sequence[Speech], duration: float, heard: Sequence[Speech] = ()) -> HeadPlan:
    """The head's motion over a shot of ``duration`` seconds with these takes, the same every build; ``heard`` is what
    the others say meanwhile (:func:`listening`)."""
    _check(style, speeches, duration)
    _check(style, heard, duration)
    spans = [span for speech in speeches for span in _breaths(speech)]
    busy = sorted([*spans, *(span for speech in heard for span in _breaths(speech))])
    nodded = [nod for k, speech in enumerate(speeches) for nod in nods(speech, style, k)]
    dipped = [t - _DIP_LEAD for speech in speeches for t in dips(speech)]
    moves = [_Move(max(0.0, t), _DIP, style.nod_px * _DIP_SHARE) for t in dipped]
    moves += [_Move(n.at, _shape(n.kind, n.span), n.amplitude) for n in nodded]
    nodding = [nod for k, speech in enumerate(heard) for nod in listening(speech, style, k, spans)]
    moves += [_Move(n.at, _shape(n.kind, n.span), n.amplitude) for n in nodding]
    rolls = [
        _Move(
            n.at,
            _shape(n.kind, n.span),
            n.amplitude / style.nod_px * style.nod_roll * (1 if hash_unit(style.seed, "roll", k) < 0.5 else -1),
        )
        for k, n in enumerate(nodded)
    ]
    leans, trails = [], []
    for k, (start, end) in enumerate(spans):
        value = style.lean * (1.0 if hash_unit(style.seed, "lean", k) < 0.5 else -1.0)
        up = min(0.7, (end - start) * 0.8)
        leans.append((start, up, end, 0.9, value))
        trails.append((start + 0.1, 0.25, start + 0.35, 0.65, -style.follow * value))
    looks = _gaze(style, speeches, busy, duration)
    lag = 0.08  # the eyes go first
    turned, slid = [], []
    for on, off, name in looks:
        side = GAZES[name][0] / GAZES["right"][0]
        turned.append((on + lag, 0.5, off, 0.6, style.glance_turn * side))
        slid.append((on + lag, 0.5, off, 0.6, style.glance_face * side))
    gaze = [state for on, off, name in looks for state in ((on, name), (off, "ahead"))]
    return HeadPlan(
        lean=Channel(_trapezoids(leans, duration), style.body),
        turn=Channel(_trapezoids([*turned, *trails], duration), style.settle),
        nod=Channel(_chain(moves, style.head, duration), style.head),
        roll=Channel(_chain(rolls, style.head, duration), style.head),
        face_x=Channel(_trapezoids(slid, duration), style.settle),
        idle_roll=Channel(_noise_keys(style, "idle_roll", style.idle_roll, busy, duration), curve="catmull-rom"),
        idle_y=Channel(_noise_keys(style, "idle_y", style.idle_px, busy, duration), curve="catmull-rom"),
        breath=Channel(_breath_keys(style, spans, duration), curve="sine-in-out"),
        gaze=tuple(gaze),
    )
