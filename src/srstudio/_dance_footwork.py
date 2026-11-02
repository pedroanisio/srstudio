"""Footwork as data, in beats (ADR 0205): what each foot does and where the weight is, over a move's loop.

A :class:`Stroke` is one thing one foot does: ``lift`` the whole foot and set it down where it was, raise the
``heel`` on the ball or the ``toe`` on the heel and lower it, ``step`` to an offset and land flat, ``touch`` an
offset with the ball and the heel up and no weight on it, ``pivot`` on the ball to a turn, or ``return`` home. A
foot's state between strokes is its offset from home (``right``, ``forward`` in hip heights of the character), its
turn from home (radians, positive toward the right) and, after a touch, the heel's lift on the ball. A stroke moves
the state on a quintic ease (smooth to the acceleration at both ends), and lifts the foot, or its heel or toe, on a
bump ``64 u^3 (1 - u)^3`` that leaves and lands with no speed and no acceleration: nothing jumps at a lift or a plant.

The strokes repeat every loop, so the state a foot holds at the loop's start is the one its last stroke leaves: two
passes over each foot's strokes settle it, and a field no stroke sets stays home.

:class:`WeightKey` places the weight: the share on the right foot at a beat, eased between keys on the same quintic
ease and wrapping round the loop. A foot in a stroke, or standing on its ball after a touch, carries at most
``UNLOADED`` of the weight, so the weight is over the other foot before this one leaves the floor and stays there until
it lands; at least one foot is flat on the floor at every moment.

A foot is planted while it is flat and in no stroke: the move's contacts are derived from its footwork, never written
beside it. The floor pass (``dance_floor``) releases every other foot from its hold and solves its leg to the goal a
frame's :class:`Steps` gives, and moves the hips toward the loaded foot by ``shift`` of the way from the feet's middle.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import checks
from ._dance_errors import MoveError

__all__ = [
    "FOOT_KINDS",
    "HOME",
    "MAX_STROKES",
    "MAX_WEIGHT_KEYS",
    "UNLOADED",
    "FootGoal",
    "Footwork",
    "Steps",
    "Stroke",
    "WeightKey",
    "bump",
    "smoother",
]

FOOT_KINDS = ("lift", "heel", "toe", "step", "touch", "pivot", "return")
FEET = ("left_foot", "right_foot")
MAX_STROKES = 32
MAX_WEIGHT_KEYS = 32
MAX_OFFSET = 1.0  # hip heights a foot may stand from home, either way
MAX_HEIGHT = 0.5  # hip heights a foot may rise off the floor
MAX_PITCH = 0.9  # radians a heel or toe may rise
MAX_FOOT_TURN = 1.2  # radians a foot may turn from home, either way
MIN_STROKE = 0.125  # beats: a stroke shorter than a 32nd note at any tempo reads as a jump
MAX_INWARD = 0.3  # hip heights a foot's home may move toward the middle or away from it
MAX_SETTLE = 0.25  # beats the hips may take to arrive over the weight
MAX_SHIFT = 1.5  # the hips may move this share of the way from the feet's middle toward the loaded foot
UNLOADED = 0.02  # the share of the weight a foot off the floor, or on its ball, may still carry
TOLERANCE = 1e-9


def smoother(u: float) -> float:
    """The quintic ease from 0 to 1: its speed and acceleration are zero at both ends."""
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def bump(u: float) -> float:
    """A lift's shape over its stroke: 0 at both ends with no speed or acceleration there, 1 half way."""
    if not 0.0 < u < 1.0:
        return 0.0
    return 64.0 * (u * (1 - u)) ** 3


def _within(value: object, low: float, high: float, what: str) -> float:
    if not (checks.number(value) and low - TOLERANCE <= value <= high + TOLERANCE):
        raise MoveError(f"{what} {value!r} lies in {low:g}..{high:g}", code="dance.footwork", path=what, actual=value)
    return float(value)


def _offset(value: object, what: str) -> tuple[float, float]:
    if not (isinstance(value, tuple) and len(value) == 2):
        raise MoveError(f"{what} is a (right, forward) pair in hip heights", code="dance.footwork", path=what)
    return (_within(value[0], -MAX_OFFSET, MAX_OFFSET, what), _within(value[1], -MAX_OFFSET, MAX_OFFSET, what))


@dataclass(frozen=True)
class _State:
    right: float = 0.0
    forward: float = 0.0
    turn: float = 0.0
    pitch: float = 0.0  # the heel's lift on the ball, held after a touch


_REQUIRED = {"step": "to", "touch": "to", "pivot": "turn"}
_LIFTS = frozenset({"lift", "step", "touch", "return"})  # kinds that may raise the whole foot
_PITCHES = frozenset({"heel", "toe", "touch", "pivot"})  # kinds that take a pitch


@dataclass(frozen=True)
class Stroke:
    """``foot`` does ``kind`` from ``start`` for ``beats`` of its move's loop (see the module's notes). ``to`` is
    where a step or touch ends, (right, forward) hip heights from home; ``height`` how high the whole foot rises,
    hip heights; ``pitch`` how far the heel (or, for ``toe``, the toes) rises, radians; ``turn`` the foot's turn from
    home once a step, touch or pivot ends, radians toward the right."""

    foot: str
    start: float
    beats: float
    kind: str
    to: tuple[float, float] | None = None
    height: float = 0.0
    pitch: float = 0.0
    turn: float | None = None

    def __post_init__(self) -> None:
        if self.foot not in FEET:
            raise MoveError(f"stroke foot {self.foot!r} is one of {FEET}", code="dance.footwork", path="foot")
        if self.kind not in FOOT_KINDS:
            raise MoveError(f"stroke kind {self.kind!r} is one of {FOOT_KINDS}", code="dance.footwork", path="kind")
        _within(self.start, 0, 64, "stroke start")
        _within(self.beats, MIN_STROKE, 64, "stroke beats")
        _within(self.height, 0, MAX_HEIGHT, "stroke height")
        _within(self.pitch, 0, MAX_PITCH, "stroke pitch")
        if self.to is not None:
            object.__setattr__(self, "to", _offset(self.to, "stroke to"))
        if self.turn is not None:
            _within(self.turn, -MAX_FOOT_TURN, MAX_FOOT_TURN, "stroke turn")
        kind = self.kind
        needed = _REQUIRED.get(kind)
        if needed and getattr(self, needed) is None:
            raise MoveError(f"a {kind} stroke says its {needed}", code="dance.footwork", path=needed)
        if self.to is not None and kind not in ("step", "touch"):
            raise MoveError(f"a {kind} stroke goes nowhere: only a step or a touch takes 'to'", path="to")
        if self.turn is not None and kind not in ("step", "touch", "pivot"):
            raise MoveError(f"a {kind} stroke does not turn the foot", code="dance.footwork", path="turn")
        if self.height and kind not in _LIFTS:
            raise MoveError(f"a {kind} stroke keeps the foot on the floor: no height", path="height")
        if self.pitch and kind not in _PITCHES:
            raise MoveError(f"a {kind} stroke lands flat: no pitch", code="dance.footwork", path="pitch")
        if kind == "lift" and self.height == 0:
            raise MoveError("a lift raises the foot: a height above 0", code="dance.footwork", path="height")
        if kind in ("heel", "toe") and self.pitch == 0:
            raise MoveError(f"a {kind} stroke raises the {kind}: a pitch above 0", path="pitch")

    @property
    def end(self) -> float:
        return self.start + self.beats

    def after(self, before: _State) -> _State:
        """The foot's state once the stroke ends, from its state before."""
        if self.kind in ("step", "touch"):
            assert self.to is not None
            turn = before.turn if self.turn is None else self.turn
            return _State(self.to[0], self.to[1], turn, self.pitch if self.kind == "touch" else 0.0)
        if self.kind == "pivot":
            assert self.turn is not None
            return replace(before, turn=self.turn)
        if self.kind == "return":
            return _State()
        return before

    def mirror(self) -> Stroke:
        """The stroke danced by the other foot, the other way round."""
        foot = FEET[1 - FEET.index(self.foot)]
        to = None if self.to is None else (-self.to[0], self.to[1])
        turn = None if self.turn is None else -self.turn
        return replace(self, foot=foot, to=to, turn=turn)


@dataclass(frozen=True)
class WeightKey:
    """The share of the weight on the right foot at ``beat`` of the loop: 0 all on the left, 1 all on the right."""

    beat: float
    right: float

    def __post_init__(self) -> None:
        _within(self.beat, 0, 64, "weight beat")
        _within(self.right, 0, 1, "weight share")


@dataclass(frozen=True)
class FootGoal:
    """Where a foot is at one moment: ``right`` and ``forward`` of home and ``up`` off the floor in hip heights,
    ``turn`` from home in radians, ``pitch`` radians raised about ``pivot`` (``ball``: the heel is up; ``heel``: the
    toes are up), and whether it stands flat and still (``planted``)."""

    right: float = 0.0
    forward: float = 0.0
    up: float = 0.0
    turn: float = 0.0
    pitch: float = 0.0
    pivot: str = "ball"
    planted: bool = True

    def mix(self, other: FootGoal, k: float) -> FootGoal:
        """This goal at ``1 - k`` and ``other`` at ``k``. A pitch reads positive on the ball and negative on the heel,
        so one about the other pivot fades out before it grows."""
        pitch = (1 - k) * self.signed + k * other.signed
        return FootGoal(
            (1 - k) * self.right + k * other.right,
            (1 - k) * self.forward + k * other.forward,
            (1 - k) * self.up + k * other.up,
            (1 - k) * self.turn + k * other.turn,
            abs(pitch),
            "ball" if pitch >= 0 else "heel",
            self.planted if k < 0.5 else other.planted,
        )

    @property
    def contacts(self) -> tuple[bool, bool]:
        """Whether the heel and the toe hold still on the floor (the static contact labels of a motion record, one
        per heel and toe, as EDGE keeps them): both on a planted foot; the toe alone while the heel is up and the
        foot turns or rises about its ball; the heel alone while the toes are up; neither in the air or while a flat
        foot moves along the floor."""
        if self.planted:
            return (True, True)
        if self.up > 0 or self.pitch == 0:
            return (False, False)
        return (False, True) if self.pivot == "ball" else (True, False)

    @property
    def signed(self) -> float:
        return self.pitch if self.pivot == "ball" else -self.pitch


HOME = FootGoal()


@dataclass(frozen=True)
class Steps:
    """A frame's footwork: each foot's goal, the share of the weight on the right foot as the footwork plans it,
    ``shift``, how far the hips move toward the loaded foot as a share of the way from the feet's middle, and
    ``settled``, the share the hips stand over, which arrives the footwork's ``settle`` after the plan."""

    left: FootGoal = HOME
    right: FootGoal = HOME
    weight: float = 0.5
    shift: float = 0.0
    settled: float = 0.5

    def contacts(self, side: str) -> tuple[bool, bool]:
        """Whether ``side``'s heel and toe hold still on the floor (:attr:`FootGoal.contacts`)."""
        return self.goal(side).contacts

    def goal(self, side: str) -> FootGoal:
        return self.left if side == "left" else self.right

    def mix(self, other: Steps | None, k: float) -> Steps:
        """This footwork at ``1 - k`` and ``other`` (home, with the weight even, when None) at ``k``."""
        other = other if other is not None else Steps()
        return Steps(
            self.left.mix(other.left, k),
            self.right.mix(other.right, k),
            (1 - k) * self.weight + k * other.weight,
            (1 - k) * self.shift + k * other.shift,
            (1 - k) * self.settled + k * other.settled,
        )


def _wrap(beat: float, loop: float) -> float:
    return beat % loop


@dataclass(frozen=True)
class Footwork:
    """A move's footwork over its loop: ``strokes`` per foot, never two at once on one foot; the ``weight`` keys;
    ``shift``, how far the hips follow the weight (see the module's notes); and ``inward``, how far each foot's home
    stands toward the middle from where the base pose puts it, in hip heights (negative: wider); ``settle``, the
    beats the hips take to arrive over the weight, so the knees, which the legs carry with the weight, move first.
    Checked against the loop by :meth:`check`, which the move calls."""

    strokes: tuple[Stroke, ...]
    weight: tuple[WeightKey, ...]
    shift: float = 1.0
    inward: float = 0.0
    settle: float = 0.0

    def __post_init__(self) -> None:
        if not (isinstance(self.strokes, tuple) and 1 <= len(self.strokes) <= MAX_STROKES):
            raise MoveError(
                f"footwork holds 1..{MAX_STROKES} strokes in a tuple", code="dance.footwork", path="strokes"
            )
        if not all(isinstance(s, Stroke) for s in self.strokes):
            raise MoveError("every stroke is a Stroke", code="dance.footwork", path="strokes")
        if not (isinstance(self.weight, tuple) and 1 <= len(self.weight) <= MAX_WEIGHT_KEYS):
            raise MoveError(f"footwork holds 1..{MAX_WEIGHT_KEYS} weight keys", code="dance.footwork", path="weight")
        if not all(isinstance(k, WeightKey) for k in self.weight):
            raise MoveError("every weight key is a WeightKey", code="dance.footwork", path="weight")
        beats = [k.beat for k in self.weight]
        if any(b <= a for a, b in zip(beats, beats[1:], strict=False)):
            raise MoveError("weight keys are in strictly rising beats", code="dance.footwork", path="weight")
        _within(self.shift, 0, MAX_SHIFT, "shift")
        _within(self.inward, -MAX_INWARD, MAX_INWARD, "inward")
        _within(self.settle, 0, MAX_SETTLE, "settle")
        for foot in FEET:
            mine = sorted((s for s in self.strokes if s.foot == foot), key=lambda s: s.start)
            if any(b.start < a.end - TOLERANCE for a, b in zip(mine, mine[1:], strict=False)):
                raise MoveError(f"{foot} does two strokes at once", code="dance.footwork", path="strokes")

    # --- the loop ---------------------------------------------------------------------------------------------------

    def check(self, loop: float, name: str) -> None:
        """Refuse footwork that does not fit a loop of ``loop`` beats: a stroke or key past it, a foot that carries
        weight off the floor, or a moment with no foot flat on the floor."""
        for s in self.strokes:
            if s.end > loop + TOLERANCE:
                raise MoveError(f"{name}: {s.foot}'s {s.kind} at {s.start:g} runs past the loop", path="strokes")
        if self.weight[-1].beat >= loop - TOLERANCE:
            raise MoveError(f"{name}: weight key at beat {self.weight[-1].beat:g} is past the loop", path="weight")
        for foot in FEET:
            for start, end in self._off(foot, loop):
                places = [start, end] + [k.beat for k in self.weight if start < k.beat < end]
                carried = max(self._load(foot, b, loop) for b in places)
                if carried > UNLOADED + TOLERANCE:
                    raise MoveError(
                        f"{name}: {foot} carries {carried:.2f} of the weight off the floor from beat {start:g}",
                        code="dance.footwork.weight",
                        path="weight",
                    )
        down = self.contacts(loop)
        reach, spans = 0.0, sorted((a, b) for _, a, b in down)
        for start, end in spans:
            if start > reach + TOLERANCE:
                break
            reach = max(reach, end)
        if reach < loop - TOLERANCE:
            raise MoveError(f"{name}: no foot is flat on the floor at beat {reach:g}", code="dance.footwork")

    def _states(self, foot: str) -> list[tuple[Stroke, _State, _State]]:
        """Each of the foot's strokes in order with its state before and after, settled round the loop."""
        mine = sorted((s for s in self.strokes if s.foot == foot), key=lambda s: s.start)
        state = _State()
        for s in mine:  # the first pass settles what the loop's last stroke leaves at its start
            state = s.after(state)
        out = []
        for s in mine:
            after = s.after(state)
            out.append((s, state, after))
            state = after
        return out

    def _off(self, foot: str, loop: float) -> list[tuple[float, float]]:
        """The spans of the loop in which ``foot`` is not flat on the floor: its strokes, and its time on the ball."""
        states = self._states(foot)
        spans = [(s.start, s.end) for s, _, _ in states]
        for i, (s, _, after) in enumerate(states):
            if after.pitch > 0:  # on the ball until the next stroke, which may come round the loop
                nxt = states[(i + 1) % len(states)][0]
                end = nxt.start if i + 1 < len(states) else nxt.start + loop
                spans.append((s.end, min(end, loop)))
                if end > loop:
                    spans.append((0.0, end - loop))
        return [(a, b) for a, b in spans if b > a + TOLERANCE]

    def contacts(self, loop: float) -> tuple[tuple[str, float, float], ...]:
        """The spans each foot is planted, as (foot, start, end) beats of the loop: flat and in no stroke."""
        out = []
        for foot in FEET:
            off = sorted(self._off(foot, loop))
            here = 0.0
            for start, end in off:
                if start > here + TOLERANCE:
                    out.append((foot, here, start))
                here = max(here, end)
            if here < loop - TOLERANCE:
                out.append((foot, here, loop))
        return tuple(out)

    def share(self, beat: float, loop: float) -> float:
        """The share of the weight on the right foot at ``beat``, eased between keys round the loop."""
        at = _wrap(beat, loop)
        keys = self.weight
        if len(keys) == 1:
            return keys[0].right
        i = next((n for n, k in enumerate(keys) if k.beat > at), len(keys))
        a, b = keys[i - 1], keys[i % len(keys)]
        start, end = a.beat, b.beat if i < len(keys) else b.beat + loop
        if at < keys[0].beat:
            start -= loop
        u = (at - start) / (end - start)
        return a.right + (b.right - a.right) * smoother(u)

    def _load(self, foot: str, beat: float, loop: float) -> float:
        right = self.share(beat, loop)
        return right if foot == "right_foot" else 1 - right

    def goal(self, foot: str, beat: float, loop: float) -> FootGoal:
        """Where ``foot`` is at ``beat`` of the grid."""
        at = _wrap(beat, loop)
        states = self._states(foot)
        if not states:
            return HOME
        held = states[-1][2]  # before its first stroke a foot stands where the loop's last stroke left it
        for s, before, after in states:
            if at < s.start:
                break
            if at < s.end:
                return _between(s, before, after, (at - s.start) / s.beats)
            held = after
        return _rest(held)

    def at(self, beat: float, loop: float) -> Steps:
        """The frame's :class:`Steps` at ``beat`` of the grid."""
        left, right = self.goal("left_foot", beat, loop), self.goal("right_foot", beat, loop)
        if self.inward:
            left = replace(left, right=left.right + self.inward)
            right = replace(right, right=right.right - self.inward)
        return Steps(left, right, self.share(beat, loop), self.shift, self.share(beat - self.settle, loop))

    def mirror(self) -> Footwork:
        """The footwork danced the other way round: each stroke by the other foot, the weight on the other side."""
        return Footwork(
            tuple(s.mirror() for s in self.strokes),
            tuple(WeightKey(k.beat, 1 - k.right) for k in self.weight),
            self.shift,
            self.inward,
            self.settle,
        )


def _rest(state: _State) -> FootGoal:
    return FootGoal(state.right, state.forward, 0.0, state.turn, state.pitch, "ball", state.pitch == 0)


def _between(s: Stroke, before: _State, after: _State, u: float) -> FootGoal:
    e, lift = smoother(u), bump(u)
    right = before.right + (after.right - before.right) * e
    forward = before.forward + (after.forward - before.forward) * e
    turn = before.turn + (after.turn - before.turn) * e
    pitch = before.pitch + (after.pitch - before.pitch) * e
    pivot = "ball"
    if s.kind == "toe":
        pivot, pitch = "heel", s.pitch * lift
    elif s.kind in ("heel", "pivot"):
        pitch += s.pitch * lift
    return FootGoal(right, forward, s.height * lift, turn, pitch, pivot, False)
