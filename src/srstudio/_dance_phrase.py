"""Dance phrases: choreography counted in eights, key poses on counts, travel and turns on the floor (ADR 0194).

A :class:`Phrase` is not a loop. It is a list of :class:`Key` poses, each on a count of its eight-counts ("and" counts
included): the canonical joints it holds, how the motion arrives on it (:data:`EASES`), where the body stands on the
floor (:class:`Floor`, in hip heights and radians), which feet carry the body, and the face. Between two keys every
joint and every floor channel moves from the first to the second on the second key's ease. A foot carries the body
from a key to the next only when both keys name it: a foot that leaves at the next key lifts as soon as this one is
reached, and a foot that lands at the next key lands on it. :func:`moment` reads a phrase at any beat.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from . import checks
from ._dance_model import FEET, ROOT, TARGETS, MoveError, _name, mirrored

__all__ = [
    "COUNT",
    "EASES",
    "HIT_SHARE",
    "MAX_EIGHTS",
    "MAX_KEYS",
    "Floor",
    "Key",
    "Moment",
    "Phrase",
    "PhraseError",
    "beat_of",
    "count_of",
    "ease",
    "moment",
]

EASES = ("smooth", "hit", "linear")
HIT_SHARE = 0.35  # a hit holds the last pose, then strikes onto the key in this share of the span before it
MAX_EIGHTS = 16
MAX_KEYS = 256
MAX_TRAVEL = 8.0  # hip heights a key may carry the body from where its phrase started, either way
MAX_FLOOR_TURN = 4 * math.pi  # two whole turns either way, within a phrase
MAX_ROUTE = 256.0  # hip heights a routine may carry the body, over all its phrases
MAX_ROUTE_TURN = 64 * math.pi
UP = (-0.5, 0.5)  # hip heights the hips may sink or rise
MAX_POSE = math.pi
COUNT = re.compile(r"([1-9][0-9]?):([1-8])([e&a]?)\Z")
_SPLIT = {"": 0.0, "e": 0.25, "&": 0.5, "a": 0.75}
_SPLIT_NAME = {0.0: "", 0.25: "e", 0.5: "&", 0.75: "a"}


class PhraseError(MoveError):
    """A phrase, key or floor outside its contract: a count off the eights, keys out of order, the body left in the
    air without a jump, a bound broken."""


def _within(value: object, low: float, high: float, what: str) -> float:
    if not (checks.number(value) and low <= value <= high):
        raise PhraseError(f"{what} {value!r} lies in {low:g}..{high:g}", code="dance.range", path=what, actual=value)
    return float(value)


def beat_of(count: str) -> float:
    """The beat a count opens, from 0 at ``"1:1"``: ``"2:5&"`` is eight 2, count 5, and: beat 12.5."""
    found = COUNT.match(count) if isinstance(count, str) else None
    if not found:
        raise PhraseError(
            f"count {count!r} is EIGHT:COUNT with an optional e, & or a, such as '1:1' or '2:5&'",
            code="dance.count",
            path="count",
            actual=count,
        )
    return (int(found.group(1)) - 1) * 8 + int(found.group(2)) - 1 + _SPLIT[found.group(3)]


def count_of(beat: float) -> str:
    """The count that opens ``beat``: the inverse of :func:`beat_of` on the sixteenth grid."""
    if not (checks.number(beat) and 0 <= beat < MAX_EIGHTS * 8 and (beat * 4) == int(beat * 4)):
        raise PhraseError(f"beat {beat!r} is a sixteenth of a count inside {MAX_EIGHTS} eights", path="beat")
    whole = int(beat)
    return f"{whole // 8 + 1}:{whole % 8 + 1}{_SPLIT_NAME[beat - whole]}"


def ease(kind: str, u: float) -> float:
    """The share of the way from one key to the next at ``u`` of the span: ``smooth`` eases out and in, ``linear``
    keeps one speed (for travel), ``hit`` holds and then strikes onto the key in the last :data:`HIT_SHARE`."""
    if kind not in EASES:
        raise PhraseError(f"ease {kind!r} is one of {EASES}", code="dance.ease", path="ease", actual=kind)
    u = min(1.0, max(0.0, u))
    if kind == "linear":
        return u
    if kind == "hit":
        u = max(0.0, (u - (1 - HIT_SHARE)) / HIT_SHARE)
    return u * u * (3 - 2 * u)


@dataclass(frozen=True)
class Floor:
    """Where the body stands: ``right`` and ``forward`` of where the phrase started, in hip heights and in the frame
    the dancer faced then; ``up`` the hips' rise (negative sinks), in hip heights; ``turn`` radians about the vertical,
    positive toward the right. Hip heights scale with the legs, so a short-legged character takes the same steps."""

    right: float = 0.0
    forward: float = 0.0
    up: float = 0.0
    turn: float = 0.0

    def __post_init__(self) -> None:
        _within(self.right, -MAX_ROUTE, MAX_ROUTE, "floor.right")
        _within(self.forward, -MAX_ROUTE, MAX_ROUTE, "floor.forward")
        _within(self.up, UP[0], UP[1], "floor.up")
        _within(self.turn, -MAX_ROUTE_TURN, MAX_ROUTE_TURN, "floor.turn")

    def then(self, other: Floor) -> Floor:
        """``other``, read from where this one leaves the body: its travel turned by this turn, the turns added. The
        rise is ``other``'s own. A routine may carry the body up to :data:`MAX_ROUTE` hip heights."""
        c, s = math.cos(self.turn), math.sin(self.turn)
        right = self.right + c * other.right + s * other.forward
        forward = self.forward - s * other.right + c * other.forward
        return Floor(right, forward, other.up, self.turn + other.turn)

    def mirror(self) -> Floor:
        return replace(self, right=-self.right, turn=-self.turn)


def _pose(value: object) -> tuple[tuple[str, float], ...]:
    if not isinstance(value, tuple):
        raise PhraseError("a key's pose is a tuple of (target, value) pairs", path="pose")
    seen: set[str] = set()
    for item in value:
        if not (isinstance(item, tuple) and len(item) == 2 and item[0] in TARGETS) or item[0] in seen:
            raise PhraseError(f"pose {item!r} is one (canonical target, value) pair per target", path="pose")
        if item[0] in ROOT:
            raise PhraseError(f"{item[0]}: a phrase moves the body with floor, not root", path="pose")
        _within(item[1], -MAX_POSE, MAX_POSE, f"pose {item[0]}")
        seen.add(item[0])
    return value


@dataclass(frozen=True)
class Key:
    """A pose on a beat of its phrase (from 0; :func:`beat_of` reads a count). ``pose`` holds joint deltas in radians,
    a joint left out at zero; ``contacts`` the feet that carry the body at this key, none only when ``airborne``."""

    beat: float
    contacts: frozenset[str]
    pose: tuple[tuple[str, float], ...] = ()
    ease: str = "smooth"
    floor: Floor = Floor()
    airborne: bool = False
    expression: str | None = None

    def __post_init__(self) -> None:
        _within(self.beat, 0, MAX_EIGHTS * 8, "beat")
        if self.beat * 4 != int(self.beat * 4):
            raise PhraseError(f"key beat {self.beat!r} lies on a sixteenth of a count", path="beat")
        if not (isinstance(self.contacts, frozenset) and self.contacts <= set(FEET)):
            raise PhraseError(f"contacts {self.contacts!r} is a frozenset of {FEET}", path="contacts")
        _pose(self.pose)
        ease(self.ease, 0.0)
        if not isinstance(self.floor, Floor):
            raise PhraseError("a key's floor is a Floor", path="floor")
        for name in ("right", "forward"):
            _within(getattr(self.floor, name), -MAX_TRAVEL, MAX_TRAVEL, f"floor.{name}")
        _within(self.floor.turn, -MAX_FLOOR_TURN, MAX_FLOOR_TURN, "floor.turn")
        if type(self.airborne) is not bool:
            raise PhraseError(f"airborne {self.airborne!r} is true or false", path="airborne")
        if self.airborne == bool(self.contacts):
            raise PhraseError(
                f"the key on {count_of(self.beat)}: a foot carries the body unless it is airborne, and none then",
                path="contacts",
            )
        if self.expression is not None:
            _name(self.expression, "expression", PhraseError)

    def mirror(self) -> Key:
        pose = tuple(mirrored(target, value) for target, value in self.pose)
        contacts = frozenset(_swap(foot) for foot in self.contacts)
        return replace(self, pose=pose, contacts=contacts, floor=self.floor.mirror())


def _swap(foot: str) -> str:
    return FEET[1 - FEET.index(foot)]


@dataclass(frozen=True)
class Phrase:
    """Choreography of ``eights`` eight-counts: keys in order from count 1 of the first eight, standing on the floor
    at the first and last key, the first where the dancer stands (no travel or turn yet)."""

    name: str
    eights: int
    keys: tuple[Key, ...]
    description: str = ""

    def __post_init__(self) -> None:
        _name(self.name, "phrase name", PhraseError)
        if type(self.eights) is not int or not 1 <= self.eights <= MAX_EIGHTS:
            raise PhraseError(f"eights {self.eights!r} is a whole number in 1..{MAX_EIGHTS}", path="eights")
        if not (isinstance(self.description, str) and len(self.description) <= 512):
            raise PhraseError("a phrase's description is text of at most 512 characters", path="description")
        if not (isinstance(self.keys, tuple) and 1 <= len(self.keys) <= MAX_KEYS):
            raise PhraseError(f"{self.name}: a phrase holds 1..{MAX_KEYS} keys in a tuple", path="keys")
        if not all(isinstance(k, Key) for k in self.keys):
            raise PhraseError(f"{self.name}: every key is a Key", path="keys")
        first, last = self.keys[0], self.keys[-1]
        if first.beat != 0 or (first.floor.right, first.floor.forward, first.floor.turn) != (0, 0, 0):
            raise PhraseError(f"{self.name}: the first key is on 1:1, where the dancer stands", path="keys")
        if first.airborne or last.airborne:
            raise PhraseError(f"{self.name}: a phrase starts and ends on the floor", path="keys")
        if last.beat >= self.beats:
            raise PhraseError(f"{self.name}: the key on beat {last.beat:g} is past {self.eights} eights", path="keys")
        for a, b in zip(self.keys, self.keys[1:], strict=False):
            if b.beat <= a.beat:
                raise PhraseError(
                    f"{self.name}: the key on {count_of(b.beat)} is not after the one before", path="keys"
                )
            if not (a.contacts & b.contacts) and not (a.airborne or b.airborne):
                raise PhraseError(
                    f"{self.name}: no foot carries the body from {count_of(a.beat)} to {count_of(b.beat)}; "
                    "keep a foot on the floor across them, or mark the jump airborne",
                    path="keys",
                )

    @property
    def beats(self) -> int:
        return 8 * self.eights

    @property
    def support(self) -> str:
        """A phrase is always danced standing."""
        return "feet"

    @property
    def end(self) -> Floor:
        """Where the phrase leaves the body, from where it started."""
        return self.keys[-1].floor

    def mirror(self) -> Phrase:
        """The phrase danced the other way round: sides swap, travel to the right goes left, turns reverse."""
        return replace(self, keys=tuple(k.mirror() for k in self.keys))

    def planted(self, beat: float) -> frozenset[str]:
        return moment(self, beat).planted


@dataclass(frozen=True)
class Moment:
    """A phrase at one beat: joint deltas, floor, the feet that carry the body, whether it is in the air, the face."""

    values: Mapping[str, float]
    floor: Floor
    planted: frozenset[str]
    airborne: bool
    expression: str | None


def _at(keys: tuple[Key, ...], beat: float) -> int:
    lo, hi = 0, len(keys)
    while lo < hi:  # the last key at or before the beat: a bisection bounded by MAX_KEYS
        mid = (lo + hi) // 2
        if keys[mid].beat <= beat:
            lo = mid + 1
        else:
            hi = mid
    return max(0, lo - 1)


def moment(phrase: Phrase, beat: float) -> Moment:
    """``phrase`` at ``beat`` from its start: the first key before it, the last key from the last key on."""
    if not isinstance(phrase, Phrase):
        raise PhraseError(f"a moment is read from a Phrase, not {type(phrase).__name__}", path="phrase")
    if not checks.number(beat):
        raise PhraseError(f"beat {beat!r} is a finite number", path="beat", actual=beat)
    keys = phrase.keys
    i = _at(keys, beat)
    a = keys[i]
    face = next((k.expression for k in reversed(keys[: i + 1]) if k.expression is not None), None)
    if i == len(keys) - 1 or beat <= a.beat:
        values = dict(a.pose)
        return Moment(MappingProxyType(values), a.floor, a.contacts, a.airborne, face)
    b = keys[i + 1]
    e = ease(b.ease, (beat - a.beat) / (b.beat - a.beat))
    first, second = dict(a.pose), dict(b.pose)
    values = {t: first.get(t, 0.0) + (second.get(t, 0.0) - first.get(t, 0.0)) * e for t in sorted({*first, *second})}
    floor = Floor(
        *(
            getattr(a.floor, n) + (getattr(b.floor, n) - getattr(a.floor, n)) * e
            for n in ("right", "forward", "up", "turn")
        )
    )
    planted = a.contacts & b.contacts
    return Moment(MappingProxyType(values), floor, planted, not planted, face)
