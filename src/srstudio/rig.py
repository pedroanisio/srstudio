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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_core.scene import Composition, Group
from sr_core.scene import Sequence as SceneSequence

from . import checks
from .canvas import Canvas, Keys
from .errors import SrstudioError
from .soundtrack import pose_keys

if TYPE_CHECKING:
    from .limbs.integration import LimbTrack
Span = tuple[float, float]


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
    ) -> Group:
        perf = perf or Performance()
        if perf.limbs and not self.supports_limbs:
            from .limbs.errors import LimbError

            raise LimbError(f"{type(self).__name__} must explicitly support replacement limb tracks")
        self.validate_performance(perf)
        cv = self.cv
        self.group = g = cv.group(parent, self.tag, x=x, y=y, scaleX=scale, scaleY=scale)
        behind = cv.group(g, f"{self.tag}-limbs-behind") if perf.limbs else None
        self.draw_body(g, perf)
        body = cv.group(g, f"{self.tag}-limbs-body") if perf.limbs else None
        self.head = head = cv.group(g, f"{self.tag_base}-head")
        self.draw_head(head, perf)
        self.eyes = eyes = cv.group(head, f"{self.tag_base}-eyes")
        self.draw_eyes(eyes, perf)
        self.draw_face_front(head, perf)
        if perf.nods:
            cv.keys(head, "rotation", perf.nods, hold=False)
        closed = cv.group(head, self.blink_id)
        self.draw_blink(closed, perf)
        if perf.blinks:
            cv.gate(closed, perf.blinks)
            cv.keys(eyes, "opacity", [(0, 1)] + [(a, 0) for a, b in perf.blinks] + [(b, 1) for a, b in perf.blinks])
        else:
            cv.gate(closed, [])
        self.mouths = self.draw_mouths(head)
        states = perf.mouth or ((0.0, "rest"),)
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
    checks.positive(scale, error, f"a character's scale must be > 0, got {scale}")
    checks.positive(end, error, f"a character is drawn for more than 0 s, got {end}")


def blinks(cv: Canvas, eyes, end: float, *, period: float, phase: float, skip_empty: bool) -> None:
    """``eyes`` close for a blink every ``period`` seconds from ``phase`` while a whole blink fits before ``end``.
    A shot too short for one keys nothing with ``skip_empty``, and holds the eyes open with a single key without
    it."""
    checks.positive(period, RigError, f"blink period must be finite and > 0, got {period!r}")
    checks.non_negative(end, RigError, f"blink end must be finite and >= 0, got {end!r}")
    checks.non_negative(phase, RigError, f"blink phase must be finite and >= 0, got {phase!r}")
    keys: list[tuple[float, float]] = [(0, 1)]
    t = phase
    while t + 0.16 < end:
        keys += [(round(t, 4), 1), (round(t + 0.05, 4), 0.1), (round(t + 0.14, 4), 1)]
        t += period
    if len(keys) > 1 or not skip_empty:
        cv.keys(eyes, "scaleY", keys, hold=False)
