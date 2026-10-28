"""Character rigs.

An :class:`Actor` draws a body, a head with eyes and a blink overlay, and five mouth
shapes that hold-keyframes switch between. Subclasses supply the drawing; the episode
supplies the performance (mouth poses, blinks, nods, gestures). The local head radius is
always 100, so ``scale`` is the on-screen head radius divided by 100.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from .canvas import Canvas, Keys
from .soundtrack import pose_keys

Span = tuple[float, float]


@dataclass
class Performance:
    """What a character does during an episode; everything is optional."""

    mouth: Sequence[tuple[float, str]] = ()  # per-frame poses from soundtrack.mouth_states
    blinks: Sequence[Span] = ()  # eyes closed inside these spans
    nods: Keys = ()  # head rotation keys (linear)
    extras: dict = field(default_factory=dict)  # rig-specific gestures, read by subclasses


class Actor(ABC):
    """Base rig: group → body, head → eyes, blink overlay, mouths."""

    role: str = "actor"
    mouth_stroke: float = 3.6

    def __init__(self, canvas: Canvas, role: str | None = None, tag: str | None = None):
        self.cv = canvas
        self.role = role or self.role
        self.tag = tag or f"{self.role}-character"
        self.group = None
        self.head = None
        self.eyes = None
        self.mouths: dict = {}

    # -- public -----------------------------------------------------------------------------
    def build(self, parent, x: float, y: float, scale: float = 1.0, perf: Performance | None = None):
        perf = perf or Performance()
        cv = self.cv
        self.group = g = cv.group(parent, self.tag, x=x, y=y, scaleX=scale, scaleY=scale)
        self.draw_body(g, perf)
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
        if perf.mouth:
            for name, shape in self.mouths.items():
                cv.keys(shape, "opacity", pose_keys(perf.mouth, name))
        self.after_head(g, perf)
        return g

    # -- hooks ----------------------------------------------------------------------------------
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
