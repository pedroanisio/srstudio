"""Regards, Dad — the sketch as data: a father writes every text message as a formal letter. His son answers yes, then
a thumbs-up, which the father reports he does not understand. The cut shows him one chair away, typing with one finger.
He asks by letter for the salt, and is passed it, and thanks his son by letter. Across the table his wife's phone
dings. She reads it aloud: "Dear Wife. Regards." She holds it. "Thirty-one years."

Collage style (ADR 0026), cast cards of ADR 0036: Gary wants Kai's respect and performs a bit nobody asked for, and
Priya's patience is graded. Gary's letters are heard in his own voice and his mouth never moves, because he is only
typing. The reel opens on a still first second (the sp-hook_motion test's
arm a): Kai, and the first letter filling his phone. ElevenLabs premade voices; only Priya's mouth is lip-synced.
"""

from __future__ import annotations

from srstudio import collage, collage_everyday, collage_sets
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import (
    TINTS,
    ZOOM_SCALE,
    CastDrawer,
    Staging,
    make_sketch,
    solo,
    stilled,
    timed,
    voices_note,
)
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4123
SLUG = "regards-dad"
TITLE = "Regards, Dad — Gary, Kai and Priya (Collage)"
NAMES = ("gary", "kai", "priya")
ROOM = "dining-room"
DESCRIPTION = (
    "A Collage sketch: a father texts his son formal letters from the next chair, and his wife gets two words."
)
ACCESSIBILITY = (
    "Paper cut-out characters at a family dining table: a kid in a red hoodie reads his phone, where each message "
    "from his father is a formal letter ending Regards, Dad. The cut shows the father beside him, typing with one "
    "finger. He asks by text for the salt and the son slides it over. Across the table the mother reads her own "
    "message, Dear Wife. Regards. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised message dings and a sting."
NOTE = "ElevenLabs premade voices Chris and Sarah at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB, and a still opening that stays still

STILL = 1.0  # the still first second: the sp-hook_motion test's arm a
FIRST = "Dear Son. Your mother asks if you have eaten. Regards, Dad."
UNDERSTOOD = "Dear Son. Understood. Regards, Dad."
UNKNOWN = "Dear Son. I do not know what this means. Regards, Dad."
THREAD = (FIRST, "yes", UNDERSTOOD, None, UNKNOWN)  # the phone's messages in order; None is the thumbs-up
SCREEN = dict(x=120.0, y=1262.0, w=840.0, h=760.0)  # Kai's phone, its foot below the frame
INSIDE = (SCREEN["x"] + collage_everyday.BEZEL, SCREEN["y"] + collage_everyday.BEZEL)
PLACES = {"kai": Place(300.0, 1880.0, 0.8), "gary": Place(790.0, 1880.0, 0.8)}
TYPING = dict(x=700.0, y=1400.0, w=180.0, h=300.0)  # Gary's phone, its back to us
READING = dict(x=450.0, y=1400.0, w=180.0, h=300.0)  # Priya's
PHONE_BACK = "#2b2d42"
HAND = ((1160.0, 1830.0), (850.0, 1500.0))  # Gary's arm in from the frame's edge, to the phone
FINGER = (802.0, 1470.0, 30.0, 88.0)  # one finger: x, y, width, length
TAP = (0.3, 22.0)  # a tap's seconds and height
PRIYA_DX = 110.0  # Priya across the table, near the shelf a zoom keeps
ZOOM_Y = 840.0  # the zoom's pivot: high enough that the cactus lands below the caption pill
SALT = (372.0, 640.0, 1800.0, 210.0)  # the shaker's start and end x, its y on the cloth, its size

LINES = (
    Line("gary", FIRST),
    Line("gary", UNDERSTOOD),
    Line("gary", UNKNOWN),
    Line("gary", "Dear Son. Pass the salt. Regards, Dad."),
    Line("gary", "Dear Son. Thank you. Regards, Dad."),
    Line("priya", "Dear Wife. Regards."),
    Line("priya", "Thirty-one years."),
)
BEATS, END = timed(
    LINES,
    (
        (1.0, "kai", "", "open", "flat", "hold"),  # the still
        (0.85, "gary", (0, 0, "Dear Son."), "open", "flat", "hold"),
        (1.35, "gary", (0, 2, "Your mother asks if you have eaten."), "open", "flat", "hold"),
        (0.95, "gary", (0, 9, "Regards, Dad."), "open", "flat", "hold"),
        (1.15, "kai", "", "open", "flat", "hold", "ding"),  # yes
        (0.85, "gary", (1, 0, "Dear Son."), "open", "flat", "hold", "ding"),
        (1.15, "gary", (1, 2, "Understood. Regards, Dad."), "open", "flat", "hold"),
        (1.2, "kai", "", "half", "flat", "hold", "ding"),  # the thumbs-up
        (0.85, "gary", (2, 0, "Dear Son."), "open", "flat", "hold", "ding"),
        (0.85, "gary", (2, 2, "I do not know what this means."), "open", "flat", "hold"),
        (1.0, "gary", (2, 9, "Regards, Dad."), "open", "flat", "hold"),
        (1.25, "kai", "", "side", "flat", "hold", "reveal:dad"),  # he has been in the next chair all along
        (0.85, "gary", (3, 0, "Dear Son."), "half", "flat", "down"),
        (1.2, "gary", (3, 2, "Pass the salt. Regards, Dad."), "half", "flat", "down"),
        (1.1, "kai", "", "side", "flat", "hold", "hiss:0.4"),  # he slides it the whole way
        (0.85, "gary", (4, 0, "Dear Son."), "half", "flat", "down", "ding"),
        (1.0, "gary", (4, 2, "Thank you. Regards, Dad."), "half", "flat", "down"),
        (0.9, "priya", "", "open", "flat", "hold", "ding"),
        (1.65, "priya", 5, "half", "flat", "hold"),
        (1.35, "priya", "", "half", "flat", "hold"),  # she lets it sit
        (1.3, "priya", 6, "closed", "smile", "hold", "zoom"),
        (0.0, "priya", "", "closed", "smile", "hold", "sting"),
    ),
    tail=0.7,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _dad(beats) -> float:
    return next(t for t, what in events(beats, "reveal") if what == "dad")


def _priya(beats) -> float:
    return next(b.start for b in beats if b.who == "priya")


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(start, 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def casting(beats, end: float) -> CastDrawer:
    """Kai alone with his phone until the reveal, whoever is writing; then the two of them; then Priya alone. Gary's
    letters never move his mouth, so his track is left out."""
    dad, priya = _dad(beats), _priya(beats)
    baffled = next(t for t, _ in events(beats, "ding")[3:4])
    reactions = {
        "kai": [
            _pose(0, "open", "flat", "hold"),
            _pose(baffled, "half", "flat", "hold"),
            _pose(dad, "side", "flat", "hold"),
        ],
        "gary": [_pose(0, "half", "flat", "down")],
    }
    lineup = Lineup(PLACES, reactions, ((dad, priya),))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        silent = {k: v for k, v in mouths.items() if k != "gary"}
        if app.start < dad:
            poses = collage.parse_poses(lineup.poses("kai", app), f"poses of kai from {app.start} s")
            collage.DRAWERS["kai"](cv, parent, poses, app.end, (), enter=app.start, mouths=())
            return collage.face(collage.LOOKS["kai"])
        if app.start < priya:
            return lineup(cv, parent, app, silent)
        moved = cv.group(parent, cv.uid("g"), x=PRIYA_DX)
        fx, fy = solo(cv, moved, app, silent)
        return collage_sets.zoom_pivot(ROOM, (fx + PRIYA_DX, min(fy, ZOOM_Y)), ZOOM_SCALE)

    return draw


def _message(cv, parent, index: int, y: float, h: float, size: float) -> None:
    """Message ``index`` of the thread in the phone, grey for Dad's, green and on the right for Kai's."""
    left = INSIDE[0] + 26
    text = THREAD[index]
    if text is None:
        collage_everyday.thumb(cv, parent, left + 600, y + h / 2, h * 0.95)
    elif index % 2:
        collage_everyday.bubble(cv, parent, text, left + 480, y, 240, min(h, 120), size=size, mine=True)
    else:
        collage_everyday.bubble(cv, parent, text, left, y, 730, h, size=size)


def _typing(cv, front, app: Appearance) -> None:
    """Gary's arm over the phone and one finger going up and down on it for the whole shot."""
    arm = cv.group(front, cv.uid("g"))
    collage_everyday.arm(cv, arm, "gary", *HAND)
    x, y, w, h = FINGER
    cv.rect(arm, x, y, w, h, collage.LOOKS["gary"].skin, collage.INK, 3, radius=14)
    period, height = TAP
    taps = int((app.end - app.start) / period)
    keyed = [(round(app.start + i * period, 6), 0.0 if i % 2 else -height) for i in range(taps + 1)]
    cv.keys(arm, "y", keyed, hold=False, local=False)


def dress(shot) -> None:
    """The thread on Kai's phone, one message on after another; the table, the phones and the salt; Priya's phone."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    dad, priya = _dad(beats), _priya(beats)
    if app.start < dad:
        collage_everyday.phone(cv, front, **SCREEN, screen="#fffaf0")
        arrived = [0.0, *(t for t, _ in events(beats, "ding")[:4])]
        newest = sum(1 for t in arrived if t <= app.start) - 1
        top = INSIDE[1] + 20
        if newest == 0:
            _message(cv, front, 0, top, 560, 66)
        else:
            _message(cv, front, newest - 1, top, 250, 46)
            _message(cv, front, newest, top + 280, 250, 46)
        return
    collage_everyday.tablecloth(cv, front)
    if app.start < priya:
        collage_everyday.phone(cv, front, **TYPING, screen=PHONE_BACK)
        _typing(cv, front, app)
        slide = events(beats, "hiss")[0][0]
        a, b, y, size = SALT
        salt = collage_everyday.salt_shaker(cv, front, a, y, size)
        cv.keys(salt, "x", [(slide, a), (slide + 0.4, b)], hold=False, local=False)
    else:
        collage_everyday.phone(cv, front, **READING, screen=PHONE_BACK)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": ROOM, "kai": ROOM, "priya": ROOM},
    dress=dress,
    cast=casting,
    still=STILL,
    opening=stilled,
    bitrate=BITRATE,
)
