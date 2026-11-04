"""Version 2 of the News frame: one band, medium close-ups and heads keyed from the speech (ADR 0238).

Version 1 is the frame :func:`srstudio.news_inked.stage` and the kit's graphics draw: the anchors at the desk at about
a third of the frame's height, and BREAKING, the lower-third, the ticker, the desk's chevron bar and the PARODY tag
stacked over its foot. A reel delivered on it keeps it. A new reel opts into this version by staging with
:func:`stage`, lettering with :func:`captions` and putting its words over the picture with :func:`band`, and draws
the same anchors, rig and set:

* **One band.** The story label (the source's credit, or BREAKING on fiction), the name kicker over its one line, and
  the ticker share one strip from :data:`BAND_TOP` to the safe area's foot, under a fifth of the frame. The show's name
  is the ticker's tab, so the band and the captions are the only two text layers on screen. The band stands down while
  an insert is up.
* **Medium close-ups.** Each shot is a camera on the version-1 set: the room, the anchors and the desk, scaled about the
  desk's middle (:class:`Framing`) so a close shot's anchor covers at least two fifths of the frame (:func:`fill`), the
  face clear of the captions over it and the band under it at every corner of what its head can reach
  (:func:`face_reach`). The room is scaled less than the desk, so it reads as further away.
* **Heads keyed from the speech.** The rig of :mod:`srstudio.news_head`, with nods sized for the closer framing
  (:data:`STYLES`) and a turn on each line's onset (:func:`onsets`): toward the other anchor on a reply, away on a line
  that follows the anchor's own, back to camera within the line. Everything is computed from the takes, so the same
  takes draw the same motion.
* **The source card off the hands.** The large card is the band itself, so it covers nothing above it; it goes before
  any hand or prop comes into the band (:func:`card_plan`), and if one is there from the first frame only the credit
  shows.
* **The PARODY tag only on fiction**: :func:`band` refuses it on a story with a source.
* **Inserts keep moving**: :func:`insert` pushes in slowly across its whole span, so a full-frame insert never holds
  a frame still.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from . import head_motion, look, news_arms, news_head, news_inked, news_kit, parts
from .brush import Point
from .canvas import Canvas
from .head_motion import FACE_UP, Facing, HeadPlan, HeadStyle
from .layout import VERTICAL, SafeArea
from .news_head import AnchorRig, Held, Said
from .news_kit import (
    CAPTION_LEADING,
    CAPTION_PAD,
    CAPTION_SIZE,
    CREAM,
    MINT,
    PLUM,
    PLUM_DEEP,
    TANGERINE,
    TICKER_SPEED,
    Act,
    Measure,
    NewsKitError,
    Pose,
    Source,
    check_copy,
)

__all__ = [
    "BAND_FOOT",
    "BAND_TOP",
    "CAPTION_FOOT",
    "CAPTION_TOP",
    "CARD_BOX",
    "CARD_LEAST",
    "EASE",
    "FRAME_H",
    "FRAME_W",
    "HEAD_TRAVEL_LEAST",
    "SHOTS",
    "STILL_MOST",
    "STYLES",
    "TEMPLATE",
    "CardPlan",
    "Framing",
    "Lower",
    "Obstacle",
    "Reach",
    "Seen",
    "band",
    "captions",
    "card_plan",
    "crown_travel",
    "face_reach",
    "fill",
    "hands_line",
    "insert",
    "insert_reach",
    "no_desk",
    "obstacles",
    "onsets",
    "phone_insert",
    "plan_of",
    "rig",
    "seen",
    "stage",
]

TEMPLATE = 2
FRAME_W, FRAME_H = 1080.0, 1920.0
_SAFE = VERTICAL.region(int(FRAME_W), int(FRAME_H))  # x 80-920, y 220-1420
EASE = news_arms.EASE  # seconds either side of a beat that the arms take to change pose

# -- the frame's lines -------------------------------------------------------------------------------------------------
CAPTION_TOP = 226.0  # the captions just under the safe area's top: no row of chips over them any more
CAPTION_FOOT = CAPTION_TOP + 2 * CAPTION_SIZE * CAPTION_LEADING + CAPTION_PAD + news_inked.DROP[1]  # with its shadow
BAND_FOOT = math.floor(_SAFE.y1)  # 1420: the Reels interface covers what is under it
BAND_H = 180.0
BAND_TOP = BAND_FOOT - BAND_H
ROW_A, ROW_A_H = BAND_TOP + 10.0, 44.0  # the label and the kicker, as chips
ROW_B, ROW_B_H = ROW_A + ROW_A_H + 6.0, 62.0  # the story's one line
TICKER_Y, TICKER_H = ROW_B + ROW_B_H + 6.0, 48.0
CHIP_SIZE, LINE_SIZE, LINE_LEAST, TICKER_SIZE = 30.0, 52.0, 36.0, 32.0
TAB_PAD = 36.0  # the ticker's tab past the show's name it carries, its point included
CARD_LINE, CARD_LEAST_SIZE = 48.0, 34.0  # the large card's headline, two lines at most
CARD_BOX = (0.0, BAND_TOP, FRAME_W, float(BAND_FOOT))  # where the large card is: the band, edge to edge
CARD_LEAST = 2.0  # seconds a large card must stay up to be read; less, and only the credit shows
FACE_GAP = 6.0  # pixels between the lowest a face reaches and the band
TILT_MOST = 6.0  # the most a pose may tilt the head in this frame: past it the chin reaches the band

# -- the heads ---------------------------------------------------------------------------------------------------------
# The nods of rig v3 sized for a head twice as big on screen, and a turn the onsets can use: Vera's dip is still small
# and late, Gus's is still loose and big (ADR 0071); both now move a head on a three-second line.
STYLES: Mapping[str, HeadStyle] = {
    "vera": replace(
        news_head.VERA_MOTION_3, nod_px=9.0, nod_roll=2.0, glance_turn=5.0, accent_db=1.5, nod_share=0.85, min_gap=0.9
    ),
    "gus": replace(news_head.GUS_MOTION_3, nod_px=12.0, nod_roll=3.0, glance_turn=6.0),
}
ONSET_LEAD = 0.2  # seconds before its first word that a line's turn starts
ONSET_HOLD = 0.9  # seconds after it that the head starts back to camera
HEAD_TRAVEL_LEAST = 15.0  # frame pixels the crown must travel over a three-second talking hold

# -- inserts -----------------------------------------------------------------------------------------------------------
STILL_MOST = 1.5  # seconds an insert may hold one frame
INSERT_AT = (500.0, 880.0)  # where the handset's middle goes: inside the safe column, under two lines of caption
INSERT_FROM, INSERT_TO = 1.16, 1.2  # its slow push: a third of the frame at the start, the safe edges at the end
_HANDSET = (
    news_inked.PHONE_X,
    news_inked.PHONE_Y,
    news_inked.PHONE_X + news_inked.PHONE_W,
    news_inked.PHONE_Y + news_inked.PHONE_H,
)
_HANDSET_MID = ((_HANDSET[0] + _HANDSET[2]) / 2, (_HANDSET[1] + _HANDSET[3]) / 2)

Span = tuple[float, float]
_DESK_Y = news_inked.DESK_Y
_MIDDLE = FRAME_W / 2


def rig(who: str, number: int = 6) -> AnchorRig:
    """``who``'s rig of version ``number`` on this frame's motion: the drawing and the seam are the version's."""
    if who not in STYLES:
        raise NewsKitError(f"the desk seats {tuple(STYLES)}, not {who!r}")
    return replace(news_inked.RIGS[f"news-{who}@{number}"], style=STYLES[who])


# -- the framing -------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Framing:
    """A shot as a camera on the version-1 set: the desk's middle at frame ``(540, desk_y)``, everything ``scale`` times
    its size there, and each anchor of ``seats`` with its middle at frame x."""

    scale: float
    desk_y: float
    seats: tuple[tuple[str, float], ...]

    def camera_x(self, x: float) -> float:
        """Where an anchor seated at frame ``x`` sits on the set."""
        return _MIDDLE + (x - _MIDDLE) / self.scale

    def frame(self, point: Point) -> Point:
        """A point of the set in frame pixels."""
        return (_MIDDLE + (point[0] - _MIDDLE) * self.scale, self.desk_y + (point[1] - _DESK_Y) * self.scale)


@dataclass(frozen=True)
class Reach:
    """Where a face can go in a framing, in frame pixels: the lowest its skin reaches, the highest its hair reaches,
    and its skin's left and right."""

    low: float
    crown: float
    left: float
    right: float


def _rotate(p: Point, degrees: float, pivot: Point) -> Point:
    a = math.radians(degrees)
    dx, dy = p[0] - pivot[0], p[1] - pivot[1]
    return (pivot[0] + dx * math.cos(a) - dy * math.sin(a), pivot[1] + dx * math.sin(a) + dy * math.cos(a))


def _hair(who: str) -> tuple[Point, ...]:
    shift = news_inked.NECK_Y - news_kit.CHIN_Y
    return tuple((x, y + shift) for x, y in rig(who).outline)


def _bounds(who: str) -> tuple[float, float]:
    """The most ``who``'s head turns either way, the pose's tilt included, and the most it drops, on this frame's
    style: the corners :func:`face_reach` measures at."""
    style = STYLES[who]
    swing = head_motion.limit(style, "turn") + head_motion.limit(style, "roll") + TILT_MOST
    return swing, head_motion.limit(style, "nod")


def _reach_local(who: str) -> Reach:
    swing, drop = _bounds(who)
    rigged = rig(who)
    skin = [_rotate(p, s * swing, rigged.neck) for s in (-1.0, 1.0) for p in rigged.head]
    hair = [_rotate(p, s * swing, rigged.neck) for s in (-1.0, 1.0) for p in _hair(who)]
    return Reach(
        low=max(y for _, y in skin) + drop,
        crown=min(y for _, y in hair),
        left=min(x for x, _ in skin),
        right=max(x for x, _ in skin),
    )


def face_reach(who: str, framing: Framing, x: float) -> Reach:
    """Where ``who``'s face, seated at frame ``x``, can go in ``framing`` at every corner of what its head reaches."""
    local = _reach_local(who)
    s = framing.scale
    return Reach(
        low=framing.desk_y + local.low * s,
        crown=framing.desk_y + local.crown * s,
        left=x + local.left * s,
        right=x + local.right * s,
    )


def _framing(scale: float, seats: tuple[tuple[str, float], ...]) -> Framing:
    """The framing at ``scale`` whose lowest face reach sits :data:`FACE_GAP` over the band."""
    low = max(_reach_local(who).low for who, _ in seats)
    return Framing(scale, round(BAND_TOP - FACE_GAP - low * scale, 2), seats)


SHOTS: Mapping[str, Framing] = {
    "vera": _framing(2.45, (("vera", _MIDDLE),)),
    "gus": _framing(2.4, (("gus", _MIDDLE),)),
    "desk": _framing(1.75, (("vera", 300.0), ("gus", 780.0))),
}


def _bust(who: str) -> Any:
    """``who``'s silhouette above the desk in bust coordinates: jacket, neck, skin and hair."""
    rigged = rig(who)
    parts_ = [
        Polygon(news_arms.TORSOS[who]),
        Polygon(rigged.head),
        Polygon(_hair(who)),
        box(-48.0, news_inked.NECK_Y - 10.0, 48.0, -150.0),
    ]
    return unary_union(parts_).intersection(box(-1000.0, -1000.0, 1000.0, 0.0))


def silhouette(framing: Framing) -> Any:
    """The anchors of ``framing`` in frame pixels, inside the frame."""
    from shapely import affinity

    shapes = [
        affinity.translate(affinity.scale(_bust(who), framing.scale, framing.scale, origin=(0, 0)), x, framing.desk_y)
        for who, x in framing.seats
    ]
    return unary_union(shapes).intersection(box(0.0, 0.0, FRAME_W, FRAME_H))


def fill(framing: Framing) -> float:
    """The share of the frame the anchors of ``framing`` cover: their silhouettes, not their boxes."""
    return float(silhouette(framing).area / (FRAME_W * FRAME_H))


def hands_line(framing: Framing) -> float:
    """The frame y of the foot of the hands lying on the desk: what is under it is the desk's front, no subject."""
    lowest = max(
        reach.wrist[1] + news_arms.BUILDS[who].hand * 1.6
        for who, _ in framing.seats
        for pair in news_arms.REACHES[who].values()
        for reach in pair
    )
    return framing.desk_y + lowest * framing.scale


# -- what the band must not cover --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Seen:
    """One shot on the reel's clock: its framing's name and, for each anchor in it, the poses from each second on."""

    start: float
    end: float
    shot: str
    poses: Mapping[str, tuple[tuple[float, Pose], ...]]


@dataclass(frozen=True)
class Obstacle:
    """A hand or a prop on screen: what it is, its box in frame pixels and when it is there."""

    what: str
    box: tuple[float, float, float, float]
    start: float
    end: float


def _during(beats: Sequence, acts: Sequence[Act], who: str, start: float, end: float) -> tuple[tuple[float, Pose], ...]:
    """``who``'s poses through a shot from ``start`` to ``end``: the one held at its start, then each beat's."""
    rows = [(b.start, getattr(act, who)) for b, act in zip(beats, acts, strict=True)]
    held = [row for row in rows if row[0] <= start][-1:]
    return tuple((max(at, start), pose) for at, pose in [*held, *(r for r in rows if start < r[0] < end)])


def seen(beats: Sequence, acts: Sequence[Act], end: float) -> tuple[Seen, ...]:
    """The shots of ``beats`` (consecutive beats of one ``who`` are one shot), with the poses of the anchors in each;
    a pose tilted past :data:`TILT_MOST` is refused, since its chin would reach the band."""
    if len(acts) != len(beats):
        raise NewsKitError(f"{len(acts)} acts for {len(beats)} beats")
    for k, act in enumerate(acts):
        for who in STYLES:
            if abs(getattr(act, who).head) > TILT_MOST:
                raise NewsKitError(
                    f"beat {k}: {who}'s head tilt {getattr(act, who).head} is past this frame's {TILT_MOST} degrees"
                )
    spans: list[tuple[str, float, float]] = []
    for b, nxt in zip(beats, [*beats[1:], None], strict=True):
        stop = end if nxt is None else nxt.start
        if spans and spans[-1][0] == b.who and spans[-1][2] == b.start:
            spans[-1] = (b.who, spans[-1][1], stop)
        else:
            spans.append((b.who, b.start, stop))
    out = []
    for who, a, b in spans:
        seats = SHOTS[who].seats if who in SHOTS else ()
        out.append(Seen(a, b, who, {anchor: _during(beats, acts, anchor, a, b) for anchor, _ in seats}))
    return tuple(out)


HAND_REACH = 64.0  # bust pixels around a wrist that its hand and fingers can take
PHONE_HELD = (-56.0, news_inked.PHONE_HELD - 94.0, 56.0, news_inked.PHONE_HELD + 86.0)  # the raised phone, ink included
PHONE_DOWN = (-100.0, 0.0, 100.0, 54.0)  # the phone face down on the desk
SHEAF = (-120.0, -30.0, 120.0, 34.0)  # Vera's papers under her hands
MUG = (news_inked.MUG_X - 60.0, news_inked.MUG_Y - 80.0, news_inked.MUG_X + 60.0, news_inked.MUG_Y + 12.0)
NOTEPAD = (16.0, _DESK_Y + 8.0, 176.0, _DESK_Y + 48.0)


def _placed(framing: Framing, local: tuple[float, float, float, float], x: float = 0.0, y: float = _DESK_Y) -> tuple:
    a = framing.frame((x + local[0], y + local[1]))
    b = framing.frame((x + local[2], y + local[3]))
    return (a[0], a[1], b[0], b[1])


def obstacles(shots: Sequence[Seen], number: int = 6) -> list[Obstacle]:
    """Every hand and prop of ``shots`` in frame pixels, each over the time it is there, a change of pose easing in
    :data:`EASE` before its beat and out after the next."""
    out: list[Obstacle] = []
    for shot in shots:
        if shot.shot not in SHOTS:
            continue
        framing = SHOTS[shot.shot]
        out += [
            Obstacle(name, _placed(framing, where), shot.start, shot.end)
            for name, where in (("mug", MUG), ("notepad", NOTEPAD))
        ]
        for who, x in framing.seats:
            cam_x = framing.camera_x(x)
            rows = shot.poses[who]
            ends = [at for at, _ in rows[1:]] + [shot.end]
            if who == "vera":
                out.append(Obstacle("vera papers", _placed(framing, SHEAF, cam_x), shot.start, shot.end))
            for (at, pose), stop in zip(rows, ends, strict=True):
                a, b = max(shot.start, at - EASE), min(shot.end, stop + EASE)
                for _, _, wrist in news_inked.skeleton(who, number, pose.arms):
                    hand = (wrist[0] - HAND_REACH, wrist[1] - HAND_REACH, wrist[0] + HAND_REACH, wrist[1] + HAND_REACH)
                    out.append(Obstacle(f"{who} hand", _placed(framing, hand, cam_x), a, b))
                if who == "gus" and pose.arms == "phone":
                    out.append(Obstacle("gus phone", _placed(framing, PHONE_HELD, cam_x), a, b))
                if who == "gus" and pose.arms == "rest":
                    out.append(Obstacle("gus phone", _placed(framing, PHONE_DOWN, cam_x), a, b))
    return out


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@dataclass(frozen=True)
class CardPlan:
    """When the large source card fills the band (None: never) and when the credit takes the label's place."""

    large: Span | None
    credit: float


def card_plan(
    shots: Sequence[Seen], start: float, small: float, least: float = CARD_LEAST, number: int = 6
) -> CardPlan:
    """The large card from ``start`` until it goes small at ``small``, or :data:`EASE` before a hand or a prop first
    comes into the band, whichever is first; shorter than ``least`` seconds, and only the credit shows, from
    ``start``. Nothing it draws is ever over a hand or a prop."""
    if not (math.isfinite(start) and math.isfinite(small) and 0 <= start <= small):
        raise NewsKitError(f"a source card needs 0 <= start <= small, got {start!r}..{small!r}")
    hits = [o.start for o in obstacles(shots, number) if _overlaps(o.box, CARD_BOX) and o.end > start]
    first = min(hits, default=math.inf)
    stop = min(small, first - EASE if first > start else start)
    if stop - start < least:
        return CardPlan(None, start)
    return CardPlan((start, stop), stop)


# -- the heads ---------------------------------------------------------------------------------------------------------
def onsets(who: str, rigged: AnchorRig, said: Said, holds: Sequence[Held], end: float) -> list[Facing]:
    """The turn on each of ``who``'s line onsets, ``(on, off, side)``: from :data:`ONSET_LEAD` before its first word
    until :data:`ONSET_HOLD` after it or the line's end, toward the other anchor when the line answers them and away
    when it follows ``who``'s own; the reel's first line is said to the camera. None overlaps a turn
    :func:`srstudio.news_head.facing` makes or a hold, and none is shorter than a turn takes."""
    base = news_head.facing(who, rigged, said, holds, end)
    held = [(h.on, h.off) for h in holds if h.who == who]
    takes = sorted((speech.words[0].start, speech.words[-1].end, by) for by, speech in said if speech.words)
    out: list[Facing] = []
    before: str | None = None
    for first, last, by in takes:
        if by == who:
            on = max(0.0, first - ONSET_LEAD)
            off = min(first + ONSET_HOLD, last, end)
            for a, _, _ in base:
                if a >= on:
                    off = min(off, a)
            busy = [(a, b) for a, b, _ in base] + held + [(a, b) for a, b, _ in out]
            side = rigged.toward if before != who else -rigged.toward
            if before is not None and off - on >= FACE_UP and not any(a < off and on < b for a, b in busy):
                out.append((round(on, 6), round(off, 6), side))
        before = by
    return out


def plan_of(who: str, rigged: AnchorRig, said: Said, holds: Sequence[Held], end: float) -> HeadPlan:
    """``who``'s head over the whole reel on this frame: nods on the stressed words of the own takes, a small one on
    the other's, the turns :func:`srstudio.news_head.facing` makes and one on each line's onset (:func:`onsets`)."""
    own = [speech for by, speech in said if by == who]
    heard = [speech for by, speech in said if by != who]
    facing = sorted([*news_head.facing(who, rigged, said, holds, end), *onsets(who, rigged, said, holds, end)])
    return head_motion.plan(rigged.style, own, end, heard=heard, facing=facing)


def crown_travel(plan: HeadPlan, who: str, scale: float, start: float, end: float, fps: int = 10) -> float:
    """The farthest the top of ``who``'s hair moves between any two of ``fps`` samples a second from ``start`` to
    ``end``, in frame pixels at ``scale``: how much a talking hold moves the head, the mouth aside."""
    hair = _hair(who)
    crown = min(hair, key=lambda p: p[1])
    pivot = (0.0, news_inked.NECK_Y)
    samples = []
    for k in range(int(round((end - start) * fps)) + 1):
        t = start + k / fps
        turn = plan.turn.sample(t) + plan.roll.sample(t) + plan.idle_roll.sample(t)
        x, y = _rotate(crown, turn, pivot)
        samples.append((x * scale, (y + plan.nod.sample(t) + plan.idle_y.sample(t)) * scale))
    return max((math.dist(a, b) for a in samples for b in samples), default=0.0)


# -- the stage ---------------------------------------------------------------------------------------------------------
ROOM_SHARE = 0.55  # how much of the camera's magnification the room takes: it is further away than the desk


def _camera(cv: Canvas, parent, framing: Framing, name: str, share: float = 1.0):
    scale = 1.0 + (framing.scale - 1.0) * share
    return cv.group(
        parent,
        name,
        x=_MIDDLE,
        y=framing.desk_y,
        anchorX=_MIDDLE,
        anchorY=_DESK_Y,
        scaleX=round(scale, 6),
        scaleY=round(scale, 6),
    )


def no_desk(cv: Canvas, parent) -> None:
    """For :class:`srstudio.toon_sketch.Staging`'s ``desk``: this frame's :func:`stage` draws the desk in each shot's
    camera, under the hands."""


def stage(
    acts: Sequence[Act], end_scan: float = 30.0, heads: bool = True, version: int | None = None
) -> Callable[[Any], None]:
    """The dress of every shot on this frame: the room, then the anchors of the shot's :class:`Framing` (``desk``
    both, ``vera`` or ``gus`` one; any other shot, an insert's, the two-shot's room and desk with nobody at it), the
    desk and the forearms over it. ``acts`` runs parallel to the sketch's beats. The heads move on :func:`plan_of` on
    the version's rig, which must be approved; ``heads=False`` draws them still. ``version`` is the anchors' version,
    by default each anchor's latest."""

    def dress(shot: Any) -> None:
        if len(acts) != len(shot.beats):
            raise NewsKitError(f"{len(acts)} acts for {len(shot.beats)} beats")
        cv, app = shot.cv, shot.app
        seen(shot.beats, acts, shot.end)  # refuses a tilt the frame cannot hold
        framing = SHOTS.get(app.who, SHOTS["desk"])
        seats = framing.seats if app.who in SHOTS else ()
        at = f"{app.who}-{round(app.start * 1000):06d}"  # one shot per who and start: an id the reel can find
        room = _camera(cv, shot.back, framing, f"tpl-room-{at}", ROOM_SHARE)
        news_inked.studio(cv, room, end_scan)
        back = _camera(cv, shot.back, framing, f"tpl-camera-{at}")
        front = _camera(cv, shot.front, framing, f"tpl-front-{at}")
        holds = news_head.holds_of(acts, shot.beats) if any(act.holds for act in acts) else ()
        for who, x in seats:
            cam_x = framing.camera_x(x)
            during = _during(shot.beats, acts, who, app.start, app.end)
            look.pool(cv, back, "news2-behind-anchor", "#0c052070", cam_x - 330, 420, 660, 760)
            news_inked._seat(cv, front, who, cam_x, 1.0)
            number = parts.latest(f"news-{who}").number if version is None else version
            motion = None
            looks: list[tuple[float, float]] = []
            if heads:
                if not news_head.approved(who, number):
                    raise NewsKitError(
                        f"news-{who}@{number}'s head rig is not approved: stage with heads=False until it is"
                    )
                rigged = rig(who, number)
                said = shot.said()
                motion = (rigged, plan_of(who, rigged, said, holds, shot.end).during(app.start, app.end))
                looks = [(on, off) for on, off, _ in news_head.facing(who, rigged, said, holds, shot.end)]
            news_inked.perform(
                cv,
                back,
                who,
                cam_x,
                during,
                app.start,
                app.end,
                shot.mouths.get(who, ()),
                over=front,
                motion=motion,
                looks=looks,
                number=number,
            )
            if who == "gus":
                down = news_kit._spans([(at, pose.arms) for at, pose in during], app.start, app.end).get("rest")
                if down:
                    news_inked._phone_down(cv, front, cam_x, down)
        news_inked.desk(cv, back)

    return dress


def captions(
    cv: Canvas,
    parent,
    lines: Sequence[Any],
    measure: Measure,
    tints: Mapping[str, str] | None = None,
    id: str = "news-captions",
    safe: SafeArea | None = VERTICAL,
):
    """The show's captions on this frame's line, :data:`CAPTION_TOP`, inside ``safe``."""
    return news_inked.captions(cv, parent, lines, measure, tints, id=id, safe=safe, top=CAPTION_TOP)


# -- the band ----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Lower:
    """A name kicker over one line of the story, from ``start`` to ``end``."""

    start: float
    end: float
    kicker: str
    line: str


def _clipped(start: float, end: float, inserts: Sequence[Span]) -> list[Span]:
    """What is left of ``start``..``end`` once the inserts' windows are taken out."""
    left, at = [], start
    for a, b in sorted(inserts):
        if a > at:
            left.append((at, min(a, end)))
        at = max(at, b)
    if at < end:
        left.append((at, end))
    return [(a, b) for a, b in left if b > a]


def _chip(cv: Canvas, parent, x: float, w: float, fill: str, text: str, ink: str, stroke: str | None = None) -> None:
    cv.rect(parent, x, ROW_A, w, ROW_A_H, fill, stroke, 3.0 if stroke else 0.0, radius=news_inked.CHIP)
    news_kit._text(cv, parent, text, x, ROW_A, w, ROW_A_H, CHIP_SIZE, ink, "center")


def _chip_w(measure: Measure, text: str) -> float:
    return math.ceil(measure(text, CHIP_SIZE) + 28.0)


def band(
    cv: Canvas,
    parent,
    *,
    ticker: Sequence[str],
    lowers: Sequence[Lower],
    end: float,
    measure: Measure,
    source: Source | None = None,
    card: CardPlan | None = None,
    parody: bool = False,
    line: str | None = None,
    inserts: Sequence[Span] = (),
    safe: SafeArea | None = VERTICAL,
    id: str = "news-band",
):
    """Every word over the picture but the captions, in one band from :data:`BAND_TOP` to :data:`BAND_FOOT`.

    A real story has a ``source``: its large card fills the band through ``card.large``, and its credit stands at the
    right of the label row from ``card.credit``. A fictional one has none and wears BREAKING at the left of that row,
    and with ``parody`` the PARODY tag at its right; :class:`NewsKitError` refuses the tag on a real story. Each of
    ``lowers`` puts its kicker on the label row and its line under it; whenever none is up, ``line``, the story's own,
    stands in that row, so the band never shows an empty one. The ticker runs under them from the end of the
    large card, its tab carrying the show's name. Nothing is drawn while an insert is up. Returns the band's group."""
    if parody and source is not None:
        raise NewsKitError("no PARODY tag on a real story: the tag is for a story the show made up")
    if not ticker or not all(isinstance(item, str) and item.strip() for item in ticker):
        raise NewsKitError("a ticker needs at least one item of words")
    if not (math.isfinite(end) and end > 0):
        raise NewsKitError(f"the band needs an end after 0, got {end!r}")
    left = news_kit.TEXT_LEFT
    right = news_inked._right(news_inked.safe_box(cv, safe))
    plan = card if card is not None else CardPlan(None, 0.0)
    if plan.large is not None and source is None:
        raise NewsKitError("a large source card needs a source")
    root = cv.group(parent, id)
    run = 0

    def window(name: str, a: float, b: float, **kw):
        nonlocal run
        run += 1
        return cv.group(root, f"{id}-{name}-{run}", start=a, end=b, **kw)

    # the strip itself, whenever no insert is up
    for a, b in _clipped(0.0, end, inserts):
        g = window("strip", a, b)
        strip = cv.grad("news-band-strip", [(0, PLUM), (1, PLUM_DEEP)], (0, 0, 0, 1))
        cv.rect(g, -20, BAND_TOP, FRAME_W + 40, BAND_H, strip)
        cv.rect(g, -20, BAND_TOP, FRAME_W + 40, 4, TANGERINE)
    # the large card: the outlet, the date and the headline, word for word
    large: list[Span] = []
    if plan.large is not None and source is not None:
        lines, size = news_kit._fit(measure, source.headline, CARD_LINE, CARD_LEAST_SIZE, right - left, 2)
        large = _clipped(*plan.large, inserts)
        tag = _chip_w(measure, source.outlet)
        for a, b in large:
            g = window("card", a, b)
            cv.rect(g, -20, BAND_TOP + 4, FRAME_W + 40, BAND_H - 4, CREAM)
            _chip(cv, g, left, tag, MINT, source.outlet, PLUM_DEEP)
            news_kit._text(cv, g, source.date, left + tag + 16, ROW_A, right - left - tag - 16, ROW_A_H, 30, PLUM)
            tall = math.ceil(len(lines) * size * 1.12) + 2
            news_kit._text(cv, g, "\n".join(lines), left, ROW_B, right - left, tall, size, PLUM_DEEP)
    after = plan.large[1] if plan.large is not None else plan.credit
    # the label row's right end: the credit, or the PARODY tag
    edge = right
    if source is not None:
        credit = f"{source.outlet}, {source.date}"
        w = _chip_w(measure, credit)
        edge = right - w - 12.0
        for a, b in _clipped(max(plan.credit, after), end, inserts):
            _chip(cv, window("credit", a, b), right - w, w, CREAM, credit, PLUM_DEEP)
    elif parody:
        w = _chip_w(measure, "PARODY")
        edge = right - w - 12.0
        for a, b in _clipped(0.0, end, inserts):
            _chip(cv, window("parody", a, b), right - w, w, PLUM_DEEP, "PARODY", news_kit.BUTTER, news_kit.BUTTER)
    start_x = left
    if source is None:
        w = _chip_w(measure, "BREAKING")
        start_x = left + w + 12.0
        for a, b in _clipped(0.0, end, inserts):
            _chip(cv, window("breaking", a, b), left, w, TANGERINE, "BREAKING", PLUM_DEEP)
    # the lowers: a kicker on the label row, its line under it
    for lower in lowers:
        if lower.end <= lower.start:
            raise NewsKitError(f"a lower-third needs start < end, got {lower.start}..{lower.end}")
        if plan.large is not None and lower.start < plan.large[1] and plan.large[0] < lower.end:
            raise NewsKitError(f"the lower {lower.kicker!r} would be up with the large card")
        kicker = check_copy(lower.kicker)
        w = _chip_w(measure, kicker)
        if start_x + w > edge:
            raise NewsKitError(f"the kicker {kicker!r} does not fit the label row beside the credit")
        lines, size = news_kit._fit(measure, check_copy(lower.line), LINE_SIZE, LINE_LEAST, right - left, 1)
        for a, b in _clipped(lower.start, lower.end, inserts):
            g = window("lower", a, b)
            _chip(cv, g, start_x, w, MINT, kicker, PLUM_DEEP)
            news_kit._text(cv, g, lines[0], left, ROW_B, right - left, ROW_B_H, size, CREAM)
    # the story's line, wherever no lower is up
    if line is not None:
        standing, standing_size = news_kit._fit(measure, check_copy(line), LINE_SIZE, LINE_LEAST, right - left, 1)
        taken = [*inserts, *((lower.start, lower.end) for lower in lowers)]
        for a, b in _clipped(after, end, taken):
            g = window("line", a, b)
            news_kit._text(cv, g, standing[0], left, ROW_B, right - left, ROW_B_H, standing_size, CREAM)
    # the ticker, from the end of the large card
    one = "   /   ".join(check_copy(item) for item in ticker) + "   /   "
    name_w = math.ceil(measure(news_kit.SHOW, TICKER_SIZE)) + 4
    tab = left + name_w + TAB_PAD
    for a, b in _clipped(after, end, inserts):
        g = window("ticker", a, b)
        cv.rect(g, -20, TICKER_Y, FRAME_W + 40, TICKER_H, CREAM)
        needed = FRAME_W + TICKER_SPEED * (b - a)
        many = one * max(1, math.ceil(needed / measure(one, TICKER_SIZE)))
        crawl = cv.group(g, f"{id}-ticker-{run}-crawl", x=FRAME_W, **({"safeAreaForce": True} if safe else {}))
        news_kit._text(
            cv, crawl, many, 0, TICKER_Y, math.ceil(measure(many, TICKER_SIZE)) + 40, TICKER_H, TICKER_SIZE, PLUM_DEEP
        )
        cv.keys(crawl, "x", [(a, tab), (b, tab - TICKER_SPEED * (b - a))], hold=False, local=False)
        cv.path(
            g,
            f"M -20 {TICKER_Y} L {tab - 24} {TICKER_Y} L {tab} {TICKER_Y + TICKER_H / 2} L {tab - 24} "
            f"{TICKER_Y + TICKER_H} L -20 {TICKER_Y + TICKER_H} Z",
            TANGERINE,
            cv.clear,
            0,
        )
        news_kit._text(cv, g, news_kit.SHOW, left, TICKER_Y, name_w, TICKER_H, TICKER_SIZE, PLUM_DEEP)
    return root


# -- inserts -----------------------------------------------------------------------------------------------------------
def insert(cv: Canvas, parent, start: float, end: float, id: str | None = None):
    """A group for a full-frame insert from ``start`` to ``end`` that pushes in from :data:`INSERT_FROM` to
    :data:`INSERT_TO` of a handset's size about :data:`INSERT_AT`, keyed at least every :data:`STILL_MOST` seconds,
    so no frame of it holds. Draw the insert into it at the kit's handset geometry."""
    news_kit._span(start, end, "an insert")
    g = cv.group(
        parent,
        id or cv.uid("tpl-insert"),
        x=INSERT_AT[0],
        y=INSERT_AT[1],
        anchorX=_HANDSET_MID[0],
        anchorY=_HANDSET_MID[1],
        scaleX=INSERT_FROM,
        scaleY=INSERT_FROM,
    )
    steps = max(1, math.ceil((end - start) / STILL_MOST))
    keys = [
        (round(start + (end - start) * k / steps, 6), round(INSERT_FROM + (INSERT_TO - INSERT_FROM) * k / steps, 6))
        for k in range(steps + 1)
    ]
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, keys, hold=False, kind="sine-in-out", local=False)
    return g


def insert_reach() -> tuple[Point, Point]:
    """The corners of a handset's screen at the insert's largest, in frame pixels: where its words can go."""

    def at(p: Point) -> Point:
        return (
            INSERT_AT[0] + (p[0] - _HANDSET_MID[0]) * INSERT_TO,
            INSERT_AT[1] + (p[1] - _HANDSET_MID[1]) * INSERT_TO,
        )

    return at((_HANDSET[0], _HANDSET[1])), at((_HANDSET[2], _HANDSET[3]))


def phone_insert(
    cv: Canvas,
    parent,
    chat: str,
    bubbles: Sequence[news_kit.Bubble],
    start: float,
    end: float,
    measure: Measure,
    id: str = "news-phone",
):
    """Gus's phone (:func:`srstudio.news_inked.phone_insert`) on this frame: a third of it and more, pushing in.
    Returns the insert's group."""
    g = insert(cv, parent, start, end)
    news_inked.phone_insert(cv, g, chat, bubbles, start, end, measure, id=id)
    return g
