"""Character rigs.

An :class:`Actor` draws a body, a head with eyes and a blink overlay, and five mouth
shapes that hold-keyframes switch between. Subclasses supply the drawing; the episode
supplies the performance (mouth poses, blinks, nods, gestures). The local head radius is
always 100, so ``scale`` is the on-screen head radius divided by 100.

:func:`check_place` and :func:`blinks` serve the lit cast (Saga, Gloss): a character's place on a shot, and eyes
that close on a style's own beat.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from sr_core.scene import Composition, Group
from sr_core.scene import Sequence as SceneSequence

from . import checks
from .canvas import Canvas, Keys, _visibility_keys
from .errors import SrstudioError, _brief, _repair
from .soundtrack import pose_keys

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack
Span = tuple[float, float]
MOUTHS = ('rest', 'round', 'open', 'small', 'smile')
MAX_BLINKS = 10_000


class RigError(SrstudioError, ValueError):
    """A rig animation setting cannot produce a valid performance."""


@dataclass
class Performance:
    """What a character does during an episode; everything is optional."""

    mouth: Sequence[tuple[float, str]] = ()  # per-frame poses from soundtrack.mouth_states
    blinks: Sequence[Span] = ()  # eyes closed inside these spans
    nods: Keys = ()  # head rotation keys (linear)
    extras: dict = field(default_factory=dict)  # rig-specific gestures, read by subclasses
    limbs: Sequence[LimbTrack] = ()

    def __post_init__(self) -> None:
        if not self.limbs:
            return
        from .limbs.errors import LimbError
        from .limbs.integration import LimbTrack

        if any(not isinstance(track, LimbTrack) for track in self.limbs):
            raise LimbError("performance limbs must be typed LimbTracks")
        sides = [track.motion.arm.side for track in self.limbs]
        if len(sides) != len(set(sides)):
            raise LimbError("performance contains duplicate tracks for one arm")
        if {"arms", "forearm", "pointing", "hide_right_arm_at", "facepalm", "held_cup"} & self.extras.keys():
            raise LimbError("typed limb tracks cannot be mixed with legacy arm controls")


class Actor(ABC):
    """Base rig: group → body, head → eyes, blink overlay, mouths."""

    role: str = "actor"
    mouth_stroke: float = 3.6
    mouth_poses: tuple[str, ...] = MOUTHS
    supports_limbs: bool = False

    def __init__(self, canvas: Canvas, role: str | None = None, tag: str | None = None):
        self.cv = canvas
        self.role = role or self.role
        self.tag = tag or f"{self.role}-character"
        self.group = None
        self.head = None
        self.eyes = None
        self.mouths: dict = {}

    # -- public -----------------------------------------------------------------------------
    def build(
        self,
        parent: Composition | Group | SceneSequence,
        x: float,
        y: float,
        scale: float = 1.0,
        perf: Performance | None = None,
        *,
        end: float | None = None,
    ) -> Group:
        """Draw the actor; ``end`` bounds limb lifetime on the canvas clock.

        Omitting it retains the project-duration default. A local character clip supplies
        its own end so a longer root track is sampled only through that clip.
        """
        if end is not None:
            if not checks.number(end) or end <= 0:
                raise RigError(
                    'actor end must be a positive finite canvas second',
                    code='rig.end',
                    path='end',
                    actual=end,
                    expected='a positive finite canvas second',
                    remedy='Set end to the actor exit time on the canvas clock, or omit it for the project end.',
                )
            end = float(end)
        if perf is None:
            perf = Performance()
        if not isinstance(perf, Performance):
            raise RigError(
                'perf must be a Performance or None',
                code='rig.performance',
                path='performance',
                actual=perf,
                expected='Performance or None',
                remedy='Construct Performance with explicit mouth, blink, nod or limb tracks.',
            )
        if perf.limbs and not self.supports_limbs:
            from .limbs.errors import LimbError

            raise LimbError(
                f"{type(self).__name__} must explicitly support replacement limb tracks",
                code='rig.limbs.unsupported',
                path='performance.limbs',
                actual=type(self).__name__,
                expected='an actor with supports_limbs=True',
                remedy='Choose a rig supporting replacement limbs or omit the limb tracks.',
            )
        self.validate_performance(perf)
        if not isinstance(perf.mouth, Sequence) or isinstance(perf.mouth, (str, bytes)):
            raise RigError(
                'mouth: expected a sequence of (project second, pose) pairs',
                code='rig.mouth.shape',
                path='performance.mouth',
                actual=perf.mouth,
                expected='a sequence of (project second, pose) pairs',
                remedy='Use an empty tuple for the default mouth, or a sequence of timed mouth poses.',
            )
        states = perf.mouth or ((0.0, 'rest'),)
        previous = 0.0
        for index, record in enumerate(states):
            if not isinstance(record, (tuple, list)) or len(record) != 2:
                raise RigError(
                    f'mouth[{index}]: expected a (project second, pose) pair',
                    code='rig.mouth.shape',
                    path=f'performance.mouth[{index}]',
                    actual=record,
                    expected='a (project second, pose) pair',
                    remedy='Provide exactly two values: the numeric time and a supported mouth pose.',
                )
            time, pose = record
            if not checks.number(time) or time < previous:
                raise RigError(
                    f'mouth[{index}]: times must be finite, non-negative and nondecreasing',
                    code='rig.mouth.time',
                    path=f'performance.mouth[{index}][0]',
                    actual=time,
                    expected={'finite': True, 'minimum': previous},
                    remedy='Order mouth states by nonnegative project seconds; use local clips for shot clocks.',
                )
            if not isinstance(pose, str) or pose not in self.mouth_poses:
                raise RigError(
                    f'mouth[{index}]: unknown pose {_brief(pose)}; expected one of {self.mouth_poses}',
                    code='rig.mouth.pose',
                    path=f'performance.mouth[{index}][1]',
                    actual=pose,
                    expected=self.mouth_poses,
                    remedy='Choose a mouth pose from this actor\'s reported vocabulary.',
                )
            previous = time
        cv = self.cv
        blink_keys = _visibility_keys(perf.blinks)
        nod_animation = None
        if perf.nods:
            # Prepare with the canvas's actual clock/freeze policy before drawing or changing actor state.
            # Reuse the validated animation so value conversion happens only once.
            staging = Group()
            nod_animation = cv.keys(staging, "rotation", perf.nods, hold=False)
            staging.remove(nod_animation)
        if perf.limbs:
            project = next(cv.scene.iter("project"), None)
            duration = end if end is not None else project.attributes().get("duration") if project is not None else None
            if duration is not None:
                from .limbs.integration import prepare_tracks

                perf = replace(perf, limbs=prepare_tracks(cv, tuple(perf.limbs), float(duration)))
        self.group = g = cv.group(parent, self.tag, x=x, y=y, scaleX=scale, scaleY=scale)
        behind = cv.group(g, f"{self.tag}-limbs-behind") if perf.limbs else None
        self.draw_body(g, perf)
        body = cv.group(g, f"{self.tag}-limbs-body") if perf.limbs else None
        self.head = head = cv.group(g, f"{self.tag_base}-head")
        self.draw_head(head, perf)
        self.eyes = eyes = cv.group(head, f"{self.tag_base}-eyes")
        self.draw_eyes(eyes, perf)
        self.draw_face_front(head, perf)
        if nod_animation is not None:
            head.add(nod_animation)
        closed = cv.group(head, self.blink_id)
        self.draw_blink(closed, perf)
        if perf.blinks:
            cv.keys(closed, "opacity", blink_keys)
            cv.keys(eyes, "opacity", [(t, 1 - value) for t, value in blink_keys])
        else:
            cv.gate(closed, [])
        self.mouths = self.draw_mouths(head)
        for name, shape in self.mouths.items():
            cv.keys(shape, "opacity", pose_keys(states, name))
        self.after_head(g, perf)
        if perf.limbs:
            from .limbs.compile import LayerTargets
            from .limbs.integration import Facing, draw_tracks

            front = cv.group(g, f"{self.tag}-limbs-front")
            draw_tracks(
                cv,
                LayerTargets(behind, body, front),
                tuple(perf.limbs),
                id=f"{self.tag}-limb",
                facing=Facing(front=True),
            )
        return g

    def replaced_arms(self, perf: Performance) -> frozenset[str]:
        """The drawn arms, named by screen side before any track, that ``perf``'s limb tracks replace. Actors face
        the viewer, so a track's anatomical right replaces the arm on screen-left."""
        if not perf.limbs:
            return frozenset()
        from .limbs.integration import Facing

        return Facing(front=True).slots(tuple(perf.limbs))

    # -- hooks ----------------------------------------------------------------------------------
    def validate_performance(self, perf: Performance) -> None:
        """Validate rig-specific extras before drawing; custom rigs may define their own contract."""
        return None

    @property
    def tag_base(self) -> str:
        """Prefix of the inner ids: ``manager`` for ``manager-character``, else the tag itself."""
        return self.tag[:-10] if self.tag.endswith("-character") else self.tag

    @property
    def blink_id(self) -> str:
        return f"{self.tag_base}-closed-eyes"

    @abstractmethod
    def draw_body(self, g, perf: Performance):
        """Required: every rig draws this part."""

    @abstractmethod
    def draw_head(self, head, perf: Performance):
        """Required: every rig draws this part."""

    @abstractmethod
    def draw_eyes(self, eyes, perf: Performance):
        """Required: every rig draws this part."""

    @abstractmethod
    def draw_blink(self, closed, perf: Performance):
        """Required: every rig draws this part."""

    def draw_face_front(self, head, perf: Performance):
        """Details drawn after the eyes (stubble, freckles); nothing by default."""
        return None

    def draw_mouths(self, head) -> dict:
        """The five poses; override the geometry, keep the names in :data:`MOUTHS`."""
        cv, ink, clear = self.cv, self.cv.ink, self.cv.clear
        sw = self.mouth_stroke
        return {
            "rest": cv.path(head, "M-7 44 L7 44", stroke=ink, sw=sw),
            "round": cv.ellipse(head, -5.5, 36, 11, 17, ink),
            "open": cv.path(head, "M-13 37 Q0 32 13 37 Q12 55 0 56 Q-11 54 -13 37Z", ink, clear, 0),
            "small": cv.ellipse(head, -10, 39, 20, 9, ink),
            "smile": cv.path(head, "M-23 37 Q0 62 24 35", stroke=ink, sw=sw),
        }

    def after_head(self, g, perf: Performance):
        """Anything drawn over the head and body (the manager's facepalm)."""
        return None


# -- the lit cast (Saga, Gloss) -------------------------------------------------------------------------------------
def check_place(scale: float, end: float, error: type[Exception]) -> None:
    """A character is drawn at a scale above 0 for a shot of more than 0 s."""
    for name, value, message in (
        ('scale', scale, "a character's scale must be > 0"),
        ('end', end, 'a character is drawn for more than 0 s'),
    ):
        if not checks.number(value) or value <= 0:
            raise _repair(
                error(f'{message}, got {_brief(value)}'),
                code='rig.placement',
                path=name,
                actual=value,
                expected='a positive finite number, excluding booleans',
                remedy='Use a positive scale and a positive exit time in the builder\'s declared clock.',
            )


def blinks(cv: Canvas, eyes, end: float, *, period: float, phase: float, skip_empty: bool) -> None:
    """``eyes`` close for a blink every ``period`` seconds from ``phase`` while a whole blink fits before ``end``.
    A shot too short for one keys nothing with ``skip_empty``, and holds the eyes open with a single key without
    it. Schedules are limited to 10,000 blinks before drawing."""
    for name, value in (('period', period), ('end', end), ('phase', phase)):
        positive = name == 'period'
        if not checks.number(value) or (value <= 0 if positive else value < 0):
            comparison = '> 0' if positive else '>= 0'
            raise RigError(
                f'blink {name} must be finite and {comparison}, got {_brief(value)}',
                code='rig.blink.input',
                path=f'blink.{name}',
                actual=value,
                expected={'finite': True, 'exclusive_minimum' if positive else 'minimum': 0},
                remedy='Use a positive blink period and nonnegative phase/end seconds.',
            )
    requested = max(0.0, (float(end) - float(phase) - 0.16) / float(period))
    if requested > MAX_BLINKS:
        raise RigError(
            'blink schedule exceeds its generation budget',
            code='rig.blink.budget',
            path='blink.period',
            actual={'period': period, 'phase': phase, 'end': end},
            expected={'maximum_blinks': MAX_BLINKS},
            remedy='Increase the blink period or shorten the schedule before retrying.',
        )
    keys: list[tuple[float, float]] = [(0, 1)]
    t = phase
    count = 0
    while t + 0.16 < end:
        if count >= MAX_BLINKS:
            raise RigError(
                'blink schedule exceeds its generation budget at float precision',
                code='rig.blink.budget',
                path='blink.period',
                actual=period,
                expected={'maximum_blinks': MAX_BLINKS},
                remedy='Increase the period or shorten the schedule.',
            )
        if t + period <= t or t + 0.05 <= t or t + 0.14 <= t + 0.05:
            raise RigError(
                'blink timestamps cannot advance at this clock precision',
                code='rig.blink.precision',
                path='blink.phase',
                actual=t,
                expected='resolvable blink timestamps',
                remedy='Use a local shot clock nearer zero, or increase the period.',
            )
        keys += [(round(t, 4), 1), (round(t + 0.05, 4), 0.1), (round(t + 0.14, 4), 1)]
        t += period
        count += 1
    if len(keys) > 1 or not skip_empty:
        cv.keys(eyes, "scaleY", keys, hold=False)
