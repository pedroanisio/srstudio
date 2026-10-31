"""How Vera's and Gus's heads move: the rig of version 2 of the News kit (ADR 0071).

The motion is :mod:`srstudio.head_motion`'s, from the takes, and it follows the speech: a nod on the stressed word, a
turn to the other anchor when they speak and back to camera for the own line, a small settle between lines. There is no
idle: a :class:`HeadStyle` here has its wander, its breath and its timed glances at zero, so a shot holds between the
lines and the face stays readable at phone size. The lean is zero too: the body, the neck and the hands never move, so a
re-render on the same takes changes only the heads. The drawing is :func:`srstudio.news_inked.perform`'s; this module
owns who faces whom and what each anchor's neck is like.

``facing`` is that default. A beat overrides it with a :class:`~srstudio.news_kit.Hold`, typed staging data that names
who an anchor faces and which later beat ends it, because a recording moves the beats and never reorders them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from . import head_motion, parts
from .brush import Point
from .head_motion import FACE_UP, Facing, HeadPlan, HeadStyle, Speech, Spring
from .news_kit import ANCHORS, Act, Hold, NewsKitError
from .toon_head import FACE_SLIDE

__all__ = [
    "GUS_MOTION",
    "VERA_MOTION",
    "AnchorRig",
    "Held",
    "Hold",
    "Said",
    "approved",
    "facing",
    "holds_of",
    "plan_of",
]

GLANCE_OFF = 600.0  # no reel runs ten minutes, so the timed glance of a style never comes
Said = Sequence[tuple[str | None, Speech]]  # each take: who said it, and the take

VERA_MOTION = HeadStyle(  # deadpan: a small dip on the word that matters, and nothing else unless the news earns it
    seed=7106,
    signature="^",
    nod_px=5.0,
    nod_roll=0.6,
    head=Spring(2.6, 0.9),
    settle=Spring(1.6, 0.95),
    body=Spring(1.2, 1.0),
    nod_share=0.4,
    min_gap=1.4,
    lead=0.06,
    accent_db=2.5,
    lean=0.0,
    follow=0.0,
    idle_roll=0.0,
    idle_px=0.0,
    breath_px=0.0,
    breath_scale=0.0,
    glance_every=GLANCE_OFF,
    glance_turn=1.6,
    glance_face=13.0,
    avert=0.0,
)
GUS_MOTION = HeadStyle(  # chaos on a loose neck: big nods that land after the word, and a head that gets there late
    seed=7107,
    signature="^",  # "~" swings up past rest and, with the nods this close, jumps 14 px in a frame
    nod_px=17.0,
    nod_roll=2.6,
    head=Spring(1.4, 0.6),
    settle=Spring(1.0, 0.6),
    body=Spring(0.9, 0.7),
    nod_share=0.9,
    min_gap=0.5,
    lead=0.0,
    lean=0.0,
    follow=0.0,
    idle_roll=0.0,
    idle_px=0.0,
    breath_px=0.0,
    breath_scale=0.0,
    glance_every=GLANCE_OFF,
    glance_turn=3.4,
    glance_face=24.0,
    avert=0.0,
)


@dataclass(frozen=True)
class AnchorRig:
    """An anchor split at the neck. ``neck`` is where the head turns and ``head`` the skin's closed contour, both on the
    bust; ``cover`` is the top of the neck, hidden behind the head, which is the seam
    (:func:`srstudio.toon_head.open_seam`). ``skin`` and ``outline`` are the skin and the hair in the head's own
    coordinates. ``toward`` is the side of the frame the other anchor is on, ``lag`` how long after the other starts
    the head goes and ``back`` how long before an own line it is back on its way to camera."""

    who: str
    style: HeadStyle
    neck: Point
    head: tuple[Point, ...]
    cover: tuple[Point, ...]
    skin: tuple[Point, ...]
    outline: tuple[Point, ...]
    toward: float
    lag: float
    back: float
    tilt: float = 0.0
    tilt_reach: tuple[float, float] = (-15.0, 15.0)  # all a Pose may ask for
    head_over: bool = True
    free: float = 0.0
    face_slide: float = FACE_SLIDE


@dataclass(frozen=True)
class Held:
    """A :class:`Hold` on the reel's clock: from its beat to the beat it names."""

    who: str
    to: str
    on: float
    off: float


def approved(who: str) -> bool:
    """Whether the record of ``who``'s rig on version 2 says approved, which only an approver's words can make it."""
    rig = parts.get(f"news-{who}").version(2).rig
    return rig is not None and rig.status == "approved"


def holds_of(acts: Sequence[Act], beats: Sequence) -> tuple[Held, ...]:
    """Every hold of ``acts``, which run parallel to ``beats``, on the clock of those beats."""
    out = []
    for k, (act, beat) in enumerate(zip(acts, beats, strict=True)):
        for hold in act.holds:
            until = next((b for b in beats[k + 1 :] if b.event == hold.until), None)
            if until is None:
                raise NewsKitError(f"{hold!r} on beat {k} needs a later beat with the event {hold.until!r}")
            out.append(Held(hold.who, hold.to, beat.start, until.start))
    return tuple(out)


def _without(spans: list[Facing], on: float, off: float) -> list[Facing]:
    kept: list[Facing] = []
    for a, b, side in spans:
        kept += [span for span in ((a, min(b, on), side), (max(a, off), b, side)) if span[1] > span[0]]
    return kept


def _joined(spans: Sequence[Facing]) -> list[Facing]:
    out: list[Facing] = []
    for a, b, side in sorted(spans):
        if out and out[-1][1] >= a and out[-1][2] == side:
            out[-1] = (out[-1][0], max(b, out[-1][1]), side)
        else:
            out.append((a, b, side))
    return out


def facing(who: str, rig: AnchorRig, said: Said, holds: Sequence[Held], end: float) -> list[Facing]:
    """When ``who`` is turned to the other anchor, ``(on, off, side)``: from just after the other starts until just
    before ``who``'s next line, which goes to camera. Each of ``who``'s holds replaces that for as long as it lasts. A
    turn too short to finish is not made."""
    lines = sorted((speech.words[0].start, by) for by, speech in said if speech.words)
    spans: list[Facing] = []
    since: float | None = None
    for at, by in lines:
        if by == who and since is not None:
            spans.append((since, at - rig.back, rig.toward))
            since = None
        elif by != who and since is None:
            since = at + rig.lag
    if since is not None:
        spans.append((since, end, rig.toward))
    for hold in (h for h in holds if h.who == who):
        spans = _without(spans, hold.on, hold.off - rig.back)
        if hold.to != "camera":
            spans.append((hold.on, hold.off - rig.back, rig.toward))
    return [span for span in _joined(spans) if span[1] - span[0] >= FACE_UP]


def plan_of(who: str, rig: AnchorRig, said: Said, holds: Sequence[Held], end: float) -> HeadPlan:
    """``who``'s head over the whole reel: their own takes to speak, the other's to hear, and who they face."""
    if who not in ANCHORS:
        raise NewsKitError(f"the desk seats {ANCHORS}, not {who!r}")
    own = [speech for by, speech in said if by == who]
    heard = [speech for by, speech in said if by != who]
    return head_motion.plan(rig.style, own, end, heard=heard, facing=facing(who, rig, said, holds, end))
