"""Head style, plan records and shared behavioral settings.

Owns the rig envelope and the plan validation boundary, independent of how a
planner derives its keys. Drawings keep their existing head_motion imports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields, replace
from typing import TypeAlias

from . import checks
from ._head_channels import Channel, HeadMotionError, Spring, _channel_bounds, _finite, _invalid
from .errors import _brief

Facing: TypeAlias = tuple[float, float, float]  # on, off, the side of the frame the head stays turned to


LOUD_RATE = 100  # loudness samples a second


PAUSE = 0.25  # the silence, in seconds, that starts a new breath


DUCK = 0.4  # how much of the idle wander is left while speaking


INTENSIFIER_GAIN = 1.5  # how much bigger a nod on an intensifier is


LISTEN_SHARE = 0.35  # how big a listener's nod is, as a share of a full nod


LISTEN_LAG = 0.15  # how long after the other's accent the listener's nod starts


FACE_UP, FACE_DOWN = 0.5, 0.6  # how long a turn takes to arrive and to come back


AVERT_BACK = 0.1  # how long before a line's first word the eyes are back


AVERT = 0.7  # how long before a line's first word they leave


ANTICIPATE = 0.08  # seconds of the small opposite move before a nod


NOD_SPAN = (0.12, 0.4)  # the shortest and longest nod, in seconds


PHONES = 3  # the letters of the stressed syllable a nod spans: Graf's two to four phones


GAZES = {"ahead": (0.0, 0.0), "left": (-0.42, 0.04), "right": (0.42, 0.04), "up": (0.0, -0.3)}  # in eye radii


LOOK_AWAY = (("left", 0.4), ("right", 0.8), ("up", 1.0))  # the share of glances each way, cumulative


CHANNELS = ("lean", "turn", "nod", "roll", "face_x", "idle_roll", "idle_y", "breath")


_ROOM = 1.25  # approved rig envelope relative to nominal targets; actual spring responses are checked


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
            raise _invalid(
                'head.style.signature',
                'style.signature',
                self.signature,
                ['^', '~', '/'],
                'Choose swing-and-back (^), overshooting swing (~), or slow shift (/).',
            )
        if type(self.seed) is not int or not checks.number(self.seed):
            raise _invalid(
                'head.style.seed',
                'style.seed',
                self.seed,
                'a finite integer, excluding booleans',
                'Choose a fixed integer seed for repeatable motion.',
            )
        for name in ('head', 'settle', 'body'):
            if not isinstance(getattr(self, name), Spring):
                raise _invalid(
                    'head.style.spring',
                    f'style.{name}',
                    getattr(self, name),
                    'a Spring',
                    'Construct Spring(frequency, damping, anticipation) for this motion phase.',
                )
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name not in ('signature', 'seed', 'head', 'settle', 'body') and not checks.number(value):
                raise _invalid(
                    'head.style.number',
                    f'style.{field.name}',
                    value,
                    'a finite number, excluding booleans',
                    'Supply the named numeric control using its documented units.',
                )
        for name in ("nod_px", "idle_hz", "breath_period", "glance_every", "glance_hold", "loud_range"):
            if getattr(self, name) <= 0:
                raise _invalid(
                    'head.style.range',
                    f'style.{name}',
                    getattr(self, name),
                    {'exclusive_minimum': 0},
                    'Use a positive value in the documented units for this control.',
                )
        for name in ("nod_roll", "min_gap", "lead", "accent_db", "lean", "idle_roll", "idle_px", "breath_px"):
            if getattr(self, name) < 0:
                raise _invalid(
                    'head.style.range',
                    f'style.{name}',
                    getattr(self, name),
                    {'minimum': 0},
                    'Use zero to disable this control, or a positive amount.',
                )
        for name in ("glance_turn", "glance_face"):
            if getattr(self, name) < 0:
                raise _invalid(
                    'head.style.range',
                    f'style.{name}',
                    getattr(self, name),
                    {'minimum': 0},
                    'Use zero to disable this control, or a positive amount.',
                )
        for name in ("nod_share", "follow", "avert"):
            if not 0 <= getattr(self, name) <= 1:
                raise _invalid(
                    'head.style.range',
                    f'style.{name}',
                    getattr(self, name),
                    {'minimum': 0, 'maximum': 1},
                    'Express this share as a fraction from zero to one.',
                )
        if not 0 <= self.breath_scale < 0.1:
            raise _invalid(
                'head.style.range',
                'style.breath_scale',
                self.breath_scale,
                {'minimum': 0, 'exclusive_maximum': 0.1},
                'Use a nonnegative scale fraction smaller than one tenth.',
            )


def limit(style: HeadStyle, name: str) -> float:
    """Allowed channel excursion; plans and figures check every curve against this envelope.

    Tuning frequency or damping does not enlarge a rig's envelope. Responses that exceed it are refused.
    """
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

    def check_gaze(self) -> None:
        """Validate all discrete states before drawing, including states outside the current shot."""
        previous = -math.inf
        if not isinstance(self.gaze, (tuple, list)):
            raise _invalid(
                'gaze.shape',
                'gaze',
                self.gaze,
                'a sequence of (second, name) pairs',
                'Provide a finite gaze track, or an empty tuple for no authored gaze.',
            )
        for index, row in enumerate(self.gaze):
            if not isinstance(row, (tuple, list)) or len(row) != 2:
                raise _invalid(
                    'gaze.shape',
                    f'gaze[{index}]',
                    row,
                    'a (second, name) pair',
                    'Supply a numeric time and a supported gaze name for each state.',
                )
            time, name = row
            if not _finite(time) or time <= previous:
                raise HeadMotionError(
                    'gaze times must be finite and strictly increasing',
                    code='gaze.time',
                    path=f'gaze[{index}][0]',
                    actual=time,
                    expected={'finite': True, 'greater_than': previous},
                    remedy='Use finite project seconds in strictly increasing order.',
                )
            if not isinstance(name, str) or name not in GAZES:
                raise HeadMotionError(
                    f'no gaze {_brief(name)}; expected one of {tuple(GAZES)}',
                    code='gaze.unknown',
                    path=f'gaze[{index}][1]',
                    actual=name,
                    expected=list(GAZES),
                    remedy='Choose one of the supported gaze states.',
                )
            previous = time

    def check_bounds(self, style: HeadStyle, *, frozen: bool = False) -> None:
        """Refuse any channel outside the style envelope, including extrema between keys.

        Endpoint-bounded easing checks its keys; splines and back/elastic easing include analytic extrema.
        Short engine springs include a conservative interpolation error bound; long carried channels are emitted
        linearly, so their sampled extrema suffice. Bare ``curve='spring'`` uses the engine's uncarried defaults.
        ``frozen`` checks only the pose emitted at zero, without sampling unused future motion.
        """
        self.check_gaze()
        for name in CHANNELS:
            channel = getattr(self, name)
            if not isinstance(channel, Channel):
                raise _invalid(
                    'head.channel.type',
                    f'head.{name}',
                    channel,
                    'a Channel',
                    'Construct Channel from numeric key pairs; use an empty Channel for zero motion.',
                )
            if not channel.keys:
                continue
            if frozen:
                from .canvas import _at_zero

                held = _at_zero(channel.keys, channel.spring is None and channel.curve == 'hold', name)
                channel = Channel(((0.0, held),))
            allowed = limit(style, name)
            bounds = _channel_bounds(channel)
            if not _finite(*bounds) or max(abs(v) for v in (*bounds, *(v for _, v in channel.keys))) > allowed + 1e-6:
                raise HeadMotionError(
                    f'{name}: curve response bound {bounds} exceeds style bound +/-{allowed:g}; '
                    'reduce the excursion or adjust curve/timing (for springs, increase damping)',
                    code='head.bounds',
                    path=f'head.{name}',
                    actual={'response_bounds': bounds},
                    expected={'minimum': -allowed, 'maximum': allowed},
                    remedy='Reduce target excursion or overshoot; adjust timing or increase spring damping.',
                )
