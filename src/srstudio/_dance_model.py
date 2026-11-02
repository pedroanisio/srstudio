"""The dance model: canonical joint targets, the waveform, patterns, moves and routines, each checked when built.

A target is ``"<joint>.<dof>"`` on the 55 joints of srlocations' mannequin, in radians, or ``"root.<axis>"`` for the
body's translation in head radii. A dof named ``a_b`` reads negative toward ``a`` and positive toward ``b``; a
single-word dof (``stretch``, ``close``, ``stretched``, ``spread``) reads positive toward that word. The skeleton
that turns these deltas into a pose owns any other convention (ADR 0186).
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from . import checks
from ._dance_curve import MAX_POINTS, MIN_POINTS, Curve
from ._dance_errors import DanceError, MoveError, RoutineError

if TYPE_CHECKING:
    from ._dance_phrase import Phrase

__all__ = [
    "CHAINS",
    "CURVE_POINTS",
    "FEET",
    "JOINTS",
    "ROOT",
    "SUPPORTS",
    "TARGETS",
    "WAVEFORMS",
    "Contact",
    "Curve",
    "DanceError",
    "Entry",
    "Move",
    "MoveError",
    "Pattern",
    "Routine",
    "RoutineError",
    "chain",
    "mirrored",
    "wave",
]

MAX_PATTERNS = 128
MAX_CONTACTS = 16
MAX_ENTRIES = 512
MAX_TRACK_BARS = 4096
MAX_ROOT = 4.0  # head radii a pattern may move the root, either way
MAX_TURN = math.pi  # radians a pattern may turn a joint, either way
NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
TOLERANCE = 1e-6


def _skeleton() -> dict[str, tuple[str, ...]]:
    torso = ("front_back", "left_right", "twist_left_right")
    look = ("nod_down_up", "tilt_left_right", "turn_left_right")
    joints: dict[str, tuple[str, ...]] = {
        "hips": torso,  # its right, up and forward (metres) are the root's translation, given here in head radii
        "spine": torso,
        "chest": torso,
        "upper_chest": torso,
        "neck": look,
        "head": look,
        "left_eye": ("down_up", "in_out"),
        "right_eye": ("down_up", "in_out"),
        "jaw": ("close", "left_right"),
    }
    for side in ("left", "right"):
        joints |= {
            f"{side}_upper_leg": ("front_back", "in_out", "twist_in_out"),
            f"{side}_lower_leg": ("stretch", "twist_in_out"),
            f"{side}_foot": ("up_down", "twist_in_out", "roll_in_out"),
            f"{side}_toes": ("up_down",),
            f"{side}_shoulder": ("down_up", "front_back"),
            f"{side}_upper_arm": ("down_up", "front_back", "twist_in_out"),
            f"{side}_lower_arm": ("stretch", "twist_in_out"),
            f"{side}_hand": ("down_up", "in_out"),
        }
        for finger in ("thumb", "index", "middle", "ring", "little"):
            for bone in ("proximal", "intermediate", "distal"):
                joints[f"{side}_{finger}_{bone}"] = ("stretched", "spread") if bone == "proximal" else ("stretched",)
    return joints


JOINTS: Mapping[str, tuple[str, ...]] = _skeleton()
ROOT = ("root.right", "root.up", "root.forward")
TARGETS = frozenset(ROOT) | frozenset(f"{joint}.{dof}" for joint, dofs in JOINTS.items() for dof in dofs)
CHAINS = ("root", "torso", "head", "left_arm", "right_arm", "left_leg", "right_leg")
SUPPORTS = ("seat", "feet", "either")
FEET = ("left_foot", "right_foot")
WAVEFORMS = ("sine", "hold", "curve")
CURVE_POINTS = (MIN_POINTS, MAX_POINTS)  # how many samples a curve holds
_TORSO = frozenset({"hips", "spine", "chest", "upper_chest"})
_HEAD = frozenset({"neck", "head", "left_eye", "right_eye", "jaw"})
_LEG = frozenset({"upper_leg", "lower_leg", "foot", "toes"})
_LATERAL = frozenset({"left_right", "twist_left_right", "tilt_left_right", "turn_left_right"})


def chain(target: str) -> str:
    """The chain a target moves with: its lag is the chain's."""
    if target not in TARGETS:
        raise MoveError(f"{target!r} is not a canonical target", code="dance.target", path="target", actual=target)
    joint = target.split(".")[0]
    if joint == "root":
        return "root"
    if joint in _TORSO:
        return "torso"
    if joint in _HEAD:
        return "head"
    side, _, rest = joint.partition("_")
    return f"{side}_leg" if rest in _LEG else f"{side}_arm"


def _swap(name: str) -> str:
    for a, b in (("left_", "right_"), ("right_", "left_")):
        if name.startswith(a):
            return b + name[len(a) :]
    return name


def mirrored(target: str, value: float) -> tuple[str, float]:
    """``target`` and ``value`` seen in a mirror: sides swap, and a central joint's sideways dof changes sign. A
    sided dof (``in_out``, ``twist_in_out``) is measured from the body's middle, so swapping the side is enough."""
    chain(target)
    joint, dof = target.split(".")
    if target == "root.right" or (joint in _TORSO | _HEAD and dof in _LATERAL):
        return target, -value
    return f"{_swap(joint)}.{dof}", value


def wave(kind: str, snap: float, u: float, curve: Curve | None = None) -> float:
    """The waveform at ``u`` of its cycle, counted from the hit: +1 at the hit, -1 at the far extreme.

    ``sine`` leaves the hit slowly, over ``1 - snap`` of the cycle, and strikes back onto it in ``snap``; both strokes
    are half cosines, so the motion eases at either extreme. ``hold`` rests at each extreme and moves between them in
    strokes of ``snap`` each, landing on the hit at ``u = 0`` and on the far extreme at ``u = 1/2``. ``curve`` plays a
    gesture's own cycle, ``curve``, and ignores ``snap`` (ADR 0199)."""
    _shape(kind, snap)
    if kind == "curve":
        if not isinstance(curve, Curve):
            raise MoveError("a curve waveform plays a Curve", code="dance.curve", path="curve")
        return curve.value(u)
    if kind == "sine":
        away = 1 - snap
        return math.cos(math.pi * u / away) if u < away else -math.cos(math.pi * (u - away) / snap)
    if u < 0.5 - snap:
        return 1.0
    if u < 0.5:
        return math.cos(math.pi * (u - (0.5 - snap)) / snap)
    if u < 1 - snap:
        return -1.0
    return -math.cos(math.pi * (u - (1 - snap)) / snap)


def _shape(kind: object, snap: object) -> None:
    if kind not in WAVEFORMS:
        raise MoveError(f"waveform {kind!r} is not one of {WAVEFORMS}", code="dance.waveform", path="waveform")
    top = 0.5 if kind == "hold" else 0.95
    if not (checks.number(snap) and 0.05 <= snap <= top):
        raise MoveError(f"snap {snap!r} of a {kind} lies in 0.05..{top}", code="dance.snap", path="snap", actual=snap)


def _within(value: object, low: float, high: float, what: str, error: type[DanceError] = MoveError) -> float:
    if not (checks.number(value) and low <= value <= high):
        raise error(f"{what} {value!r} lies in {low}..{high}", code="dance.range", path=what, actual=value)
    return float(value)


def _name(value: object, what: str, error: type[DanceError]) -> str:
    if not (isinstance(value, str) and len(value) <= 64 and NAME.match(value)):
        raise error(f"{what} {value!r} is a lowercase, hyphenated name of at most 64 characters", path=what)
    return value


def _bound(target: str) -> float:
    return MAX_ROOT if target in ROOT else MAX_TURN


@dataclass(frozen=True)
class Pattern:
    """One channel's motion: ``bias + intensity * amplitude * wave(...)``, hitting ``+amplitude`` every cycle.

    ``cycles`` count per ``beat`` or per ``bar``; the hit lands ``phase`` beats after the grid's beat; ``swing`` is
    where the off-beat eighth lands in the beat (0.5 straight, 2/3 a triplet swing). Amplitudes and biases are head
    radii on the root and radians on a joint, so a move scales to any character. A ``curve`` waveform carries the
    gesture's own cycle in ``curve``, samples from the hit (ADR 0199); no other waveform takes samples."""

    target: str
    amplitude: float
    cycles: float = 1.0
    per: str = "beat"
    phase: float = 0.0
    waveform: str = "sine"
    snap: float = 0.5
    swing: float = 0.5
    intensity: float = 1.0
    bias: float = 0.0
    curve: tuple[float, ...] = ()
    shape: Curve | None = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        chain(self.target)
        bound = _bound(self.target)
        _within(self.amplitude, -bound, bound, "amplitude")
        _within(self.bias, -bound, bound, "bias")
        if self.amplitude == 0 and self.bias == 0:
            raise MoveError(f"{self.target}: a pattern moves or holds something", path="amplitude")
        _within(self.cycles, 1e-3, 16, "cycles")
        if self.per not in ("beat", "bar"):
            raise MoveError(f"per {self.per!r} is 'beat' or 'bar'", path="per", actual=self.per)
        _within(self.phase, -64, 64, "phase")
        _shape(self.waveform, self.snap)
        _within(self.swing, 0.5, 0.75, "swing")
        _within(self.intensity, 0, 2, "intensity")
        if self.waveform == "curve":
            shape = Curve(self.curve)
            object.__setattr__(self, "shape", shape)
            object.__setattr__(self, "curve", shape.points)
        elif self.curve != ():
            raise MoveError(
                f"{self.target}: only a curve waveform takes samples, not {self.waveform}",
                code="dance.curve",
                path="curve",
            )
        else:
            object.__setattr__(self, "shape", None)

    def wave(self, u: float, snap: float | None = None) -> float:
        """The pattern's waveform at ``u`` of its cycle, with ``snap`` in place of its own when given."""
        return wave(self.waveform, self.snap if snap is None else snap, u, self.shape)

    def timing(self) -> tuple[float, str, float, str, float, tuple[float, ...]]:
        """What places the pattern in time: two patterns that share it differ only in size and shape."""
        return (self.cycles, self.per, self.phase, self.waveform, self.swing, self.curve)

    def cycles_per_beat(self, beats_per_bar: int) -> float:
        return self.cycles if self.per == "beat" else self.cycles / beats_per_bar


@dataclass(frozen=True)
class Contact:
    """``foot`` is planted from ``start`` to ``end`` beats of its move's loop, the end excluded."""

    foot: str
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.foot not in FEET:
            raise MoveError(f"contact foot {self.foot!r} is one of {FEET}", path="foot", actual=self.foot)
        _within(self.start, 0, 64, "contact start")
        _within(self.end, 0, 64, "contact end")
        if self.end <= self.start:
            raise MoveError(f"contact {self.start}..{self.end} ends after it starts", path="contact")


def _lags(value: object) -> dict[str, float]:
    if not isinstance(value, tuple):
        raise MoveError("lags are a tuple of (chain, beats) pairs", path="lags")
    out: dict[str, float] = {}
    for item in value:
        if not (isinstance(item, tuple) and len(item) == 2 and item[0] in CHAINS):
            raise MoveError(f"lag {item!r} is a (chain, beats) pair with a chain of {CHAINS}", path="lags")
        if item[0] in out:
            raise MoveError(f"chain {item[0]} has one lag", path="lags")
        out[item[0]] = _within(item[1], 0, 1, "lag")
    return out


@dataclass(frozen=True)
class Move:
    """A named dance move: patterns on canonical targets, a lag in beats per chain, and how the body is held up.

    ``support`` is ``seat`` (the seat holds the body: no legs), ``feet`` (standing: ``contacts`` plant the feet over a
    loop of ``loop_beats``, at least one foot at every moment) or ``either`` (upper body only, no root or legs: a
    standing body keeps both feet planted). Planting a foot is the body's job; a contact only says when."""

    name: str
    support: str
    patterns: tuple[Pattern, ...]
    loop_beats: float = 1.0
    lags: tuple[tuple[str, float], ...] = ()
    contacts: tuple[Contact, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        _name(self.name, "move name", MoveError)
        if self.support not in SUPPORTS:
            raise MoveError(f"support {self.support!r} is one of {SUPPORTS}", path="support", actual=self.support)
        if not (isinstance(self.description, str) and len(self.description) <= 512):
            raise MoveError("a move's description is text of at most 512 characters", path="description")
        if not (isinstance(self.patterns, tuple) and 1 <= len(self.patterns) <= MAX_PATTERNS):
            raise MoveError(f"{self.name}: a move holds 1..{MAX_PATTERNS} patterns in a tuple", path="patterns")
        if not all(isinstance(p, Pattern) for p in self.patterns):
            raise MoveError(f"{self.name}: every pattern is a Pattern", path="patterns")
        targets = [p.target for p in self.patterns]
        if len(set(targets)) != len(targets):
            raise MoveError(f"{self.name}: a target has one pattern", path="patterns")
        _within(self.loop_beats, 0.25, 64, "loop_beats")
        _lags(self.lags)
        self._support(targets)
        for p in self.patterns:
            turns = p.cycles * self.loop_beats
            if p.per == "beat" and abs(turns - round(turns)) > TOLERANCE:
                raise MoveError(
                    f"{self.name}: {p.target} turns {turns:g} times in the {self.loop_beats:g}-beat loop; "
                    "a loop holds whole cycles",
                    path="loop_beats",
                )

    def _support(self, targets: list[str]) -> None:
        chains = {chain(t) for t in targets}
        legs = chains & {"left_leg", "right_leg"}
        if self.support != "feet":
            if legs:
                raise MoveError(f"{self.name}: a {self.support}-supported move has no leg patterns", path="patterns")
            if self.support == "either" and "root" in chains:
                raise MoveError(f"{self.name}: an either-supported move leaves the root to the body", path="patterns")
            if self.contacts != ():
                raise MoveError(f"{self.name}: only a standing move plants feet", path="contacts")
            return
        if not (isinstance(self.contacts, tuple) and 1 <= len(self.contacts) <= MAX_CONTACTS):
            raise MoveError(f"{self.name}: a standing move plants feet in 1..{MAX_CONTACTS} contacts", path="contacts")
        if not all(isinstance(c, Contact) for c in self.contacts):
            raise MoveError(f"{self.name}: every contact is a Contact", path="contacts")
        for c in self.contacts:
            if c.end > self.loop_beats + TOLERANCE:
                raise MoveError(f"{self.name}: contact {c.start}..{c.end} runs past the loop", path="contacts")
        for foot in FEET:
            spans = sorted((c.start, c.end) for c in self.contacts if c.foot == foot)
            if any(b[0] < a[1] for a, b in zip(spans, spans[1:], strict=False)):
                raise MoveError(f"{self.name}: {foot} is planted twice at once", path="contacts")
        reach = 0.0
        for start, end in sorted((c.start, c.end) for c in self.contacts):
            if start > reach + TOLERANCE:
                break
            reach = max(reach, end)
        if reach < self.loop_beats - TOLERANCE:
            raise MoveError(f"{self.name}: no foot is planted from beat {reach:g} of the loop", path="contacts")

    def lag(self, chain_name: str) -> float:
        if chain_name not in CHAINS:
            raise MoveError(f"chain {chain_name!r} is one of {CHAINS}", path="chain")
        return dict(self.lags).get(chain_name, 0.0)

    def planted(self, beat: float) -> frozenset[str]:
        """The feet planted at ``beat`` of the grid: a standing move's contacts, both feet on ``either``, none on a
        seat."""
        if self.support == "seat":
            return frozenset()
        if self.support == "either":
            return frozenset(FEET)
        at = beat % self.loop_beats
        return frozenset(c.foot for c in self.contacts if c.start <= at < c.end)

    def held(self) -> tuple[tuple[str, float], ...]:
        """The pose a move that never moves holds, as an :attr:`Entry.hold`: each pattern's bias by target. A move
        with a moving pattern is refused, because a hold has no beat to move on (ADR 0192)."""
        moving = [p.target for p in self.patterns if p.amplitude != 0]
        if moving:
            raise MoveError(f"{self.name}: {moving} move, so the move is no held pose", path="patterns", actual=moving)
        return tuple((p.target, p.bias) for p in self.patterns)

    def mirror(self) -> Move:
        """The move danced the other way round."""
        patterns = []
        for p in self.patterns:
            target, amplitude = mirrored(p.target, p.amplitude)
            patterns.append(replace(p, target=target, amplitude=amplitude, bias=mirrored(p.target, p.bias)[1]))
        lags = tuple((_swap(name), beats) for name, beats in self.lags)
        contacts = tuple(Contact(_swap(c.foot), c.start, c.end) for c in self.contacts)
        return Move(self.name, self.support, tuple(patterns), self.loop_beats, lags, contacts, self.description)


def _phrase_type() -> type:
    from ._dance_phrase import Phrase  # the phrase model reads this module's targets, so it is imported on use

    return Phrase


@dataclass(frozen=True)
class Entry:
    """A move or a phrase danced over bars ``start_bar``..``end_bar`` (end excluded), with the face held for the phrase.

    A :class:`Phrase` (ADR 0194) is danced from its first count, as many times in a row as the entry holds it; each
    time starts where the last left the body on the floor.

    ``transition_beats`` crossfade the move's parameters in from the entry that ends where this one starts, or from
    rest; ``hold`` is a held pose (a head turn, say) added to the move and crossfaded the same way. ``mirror`` turns the
    move round and leaves ``hold`` as written: a held pose already says which way it faces."""

    start_bar: int
    end_bar: int
    move: Move | Phrase
    intensity: float = 1.0
    mirror: bool = False
    transition_beats: float = 0.0
    expression: str | None = None
    hold: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        for value in (self.start_bar, self.end_bar):
            if type(value) is not int or not 0 <= value <= MAX_TRACK_BARS:
                raise RoutineError(f"bar {value!r} is a whole bar in 0..{MAX_TRACK_BARS}", path="bars", actual=value)
        if self.end_bar <= self.start_bar:
            raise RoutineError(f"entry {self.start_bar}..{self.end_bar} ends after it starts", path="bars")
        if not isinstance(self.move, (Move, _phrase_type())):
            raise RoutineError(f"entry {self.start_bar}..{self.end_bar} dances a Move or a Phrase", path="move")
        _within(self.intensity, 0, 2, "intensity", RoutineError)
        if type(self.mirror) is not bool:
            raise RoutineError(f"mirror {self.mirror!r} is true or false", path="mirror")
        _within(self.transition_beats, 0, 4 * MAX_TRACK_BARS, "transition_beats", RoutineError)
        if self.expression is not None:
            _name(self.expression, "expression", RoutineError)
        if not isinstance(self.hold, tuple):
            raise RoutineError("hold is a tuple of (target, value) pairs", path="hold")
        seen: set[str] = set()
        for item in self.hold:
            if not (isinstance(item, tuple) and len(item) == 2 and item[0] in TARGETS) or item[0] in seen:
                raise RoutineError(f"hold {item!r} is one (canonical target, value) pair per target", path="hold")
            seen.add(item[0])
            bound = _bound(item[0])
            _within(item[1], -bound, bound, f"hold {item[0]}", RoutineError)

    def danced(self) -> Move | Phrase:
        return self.move.mirror() if self.mirror else self.move


@dataclass(frozen=True)
class Routine:
    """Choreography on a track of ``track_bars`` bars of ``beats_per_bar``: entries in order, never overlapping, with
    rest between them. A routine is seated or standing throughout: it never mixes seat and feet moves."""

    track_bars: int
    entries: tuple[Entry, ...]
    beats_per_bar: int = 4
    support: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.track_bars) is not int or not 1 <= self.track_bars <= MAX_TRACK_BARS:
            raise RoutineError(f"track_bars {self.track_bars!r} lies in 1..{MAX_TRACK_BARS}", path="track_bars")
        if type(self.beats_per_bar) is not int or not 1 <= self.beats_per_bar <= 16:
            raise RoutineError(f"beats_per_bar {self.beats_per_bar!r} lies in 1..16", path="beats_per_bar")
        if not (isinstance(self.entries, tuple) and 1 <= len(self.entries) <= MAX_ENTRIES):
            raise RoutineError(f"a routine holds 1..{MAX_ENTRIES} entries in a tuple", path="entries")
        if not all(isinstance(e, Entry) for e in self.entries):
            raise RoutineError("every entry is an Entry", path="entries")
        last = 0
        for i, e in enumerate(self.entries):
            if e.start_bar < last:
                raise RoutineError(f"entries[{i}] starts at bar {e.start_bar}, inside the entry before", path="entries")
            if e.end_bar > self.track_bars:
                raise RoutineError(
                    f"entries[{i}] ends at bar {e.end_bar}, past the track's {self.track_bars}", path="entries"
                )
            beats = (e.end_bar - e.start_bar) * self.beats_per_bar
            if not isinstance(e.move, Move) and beats % e.move.beats:
                raise RoutineError(
                    f"entries[{i}] holds {beats} beats, not a whole number of {e.move.name}'s {e.move.beats}",
                    path="entries",
                )
            if e.transition_beats > beats:
                raise RoutineError(
                    f"entries[{i}]'s transition of {e.transition_beats:g} beats is longer than the entry",
                    path="transition_beats",
                )
            last = e.end_bar
        supports = {e.move.support for e in self.entries}
        if {"seat", "feet"} <= supports:
            raise RoutineError("a routine is seated or standing: it never mixes seat and feet moves", path="entries")
        object.__setattr__(self, "support", next((s for s in ("seat", "feet") if s in supports), "either"))
