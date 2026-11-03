"""Big Font — the sketch as data: Rosa at the table, her phone on the largest text size there is, texting her sister
about Gary in front of him. He reads it out over the soup, flat as a newsreader. Mom, I can read it. No, you can't.
STILL SINGLE? DON'T ASK. HE GETS SAD. Gary takes out his own phone, tilts it away from her and types to his brother in
small ordinary type. She has not looked up.
"Tell your brother I can read that."

Collage style (ADR 0026), Okayville batch send-v2: the recipient is your mom, and the opening line is the viewer's. The
Collage busts free one arm at a time, so Rosa's other hand is under the table and she types with the one in the frame,
which also leaves her cane with no hand on it. ElevenLabs premade voices, lip-synced. No Collage spoon exists, so the
spoon going down is heard and not seen. Gary's read of the first line is under a second and the opening line needs
2.18 s up, so he reads from 1.3 s, over her phone already showing his name.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from srstudio import collage, collage_big_type, collage_everyday, collage_forecast, foley, opener
from srstudio.collage_forecast import Message
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Overlay, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances, events
from srstudio.staging import StagingError

SEED = 3509
SLUG = "big-font"
TITLE = "Big Font — Rosa and Gary (Collage)"
NAMES = ("rosa", "gary")
ROOM = "dining-room"
DESCRIPTION = (
    "A Collage sketch: a mother texts her sister about her son across the table in the largest font a phone has, and "
    "he reads it aloud, until he texts his brother and she reads that too."
)
ACCESSIBILITY = (
    "Paper cut-out characters at a dining table with a bowl of soup. An older woman holds up a phone whose screen "
    "shows two huge words at a time, and her son reads them aloud. He takes out his own phone and types a small "
    "message. Lines appear in tinted pills."
)
NARRATION = (
    f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesized phone taps, a phone buzz and a small "
    "clink on a bowl."
)
NOTE = "ElevenLabs premade voices Matilda and Chris at their natural pace; no reference-voice cloning."

TEXT = "my mom texting about\nme in giant font"
OPENER_TOP = 222.0  # under the bug's height, inside the vertical safe area
UNDER_OPENER = 380.0  # the pill's top while the opening line is up: its two rows end at 366

PLACES = {"gary": Place(230.0, 1760.0, 0.8), "rosa": Place(850.0, 1760.0, 0.8)}  # his eyes go sideways to her phone
TWO_SHOT_PHONE = dict(x=380.0, y=770.0, w=320.0, h=540.0, tilt=3.0)  # between their faces
TWO_SHOT_HAND = (668.0, 1290.0)  # her thumb on the phone's foot, clear of its words
TWO_SHOT_TABLE = 1500.0
SOUP = (540.0, 1590.0, 300.0)
ROSA_X = 170.0
GARY_X = -100.0
ROSA_PHONE = dict(x=150.0, y=1000.0, w=360.0, h=640.0)  # in her close: her side of the frame, the phone on the other
ROSA_HAND = (474.0, 1600.0)
INSERT = dict(x=150.0, y=790.0, w=780.0, h=1090.0)  # clear of the shelf above and of the pill
NEAR_SCALE = 1.9  # a phone up at the eye, so the hand is near as well
NEAR_HAND = (864.0, 1820.0)
NEAR_ELBOW = (1120.0, 2040.0)
CORNER_PHONE = dict(x=630.0, y=1130.0, w=340.0, h=600.0, tilt=6.0)  # her phone, in the corner of his close
CORNER_ELBOW = (1280.0, 1980.0)
CORNER_HAND = (920.0, 1700.0)
TABLE = 1640.0
GARY_SOUP = (200.0, 1760.0, 300.0)
BACK = "#2b2d42"  # the back of Gary's phone, tilted away from her
OWN_PHONE = dict(w=160.0, h=280.0, tilt=-10.0)  # narrow enough to leave both his hands in sight on it
OWN_DOWN = 1660.0  # behind the table's edge
OWN_UP = 1340.0  # the top of his phone, up at his chest
OWN_RISE = 0.25
TAP = (0.3, 8.0)  # seconds a tap, pixels her hand dips
SMALL_TAPS = 0.11  # seconds between Gary's fast small taps
SPOON_GAIN = -12.0
TAP_GAIN = -19.0
BITRATE = 5_800_000  # bits a second: the grain, new every frame, otherwise costs the size; encoded in software
KEYFRAMES = 7.0  # with no B frames, the grain leaves x264 its cuts (ADR 0083)

LINES = (
    Line("gary", "Gary. Looks. Thin."),
    Line("rosa", "I'm texting my sister."),
    Line("gary", "Mom. I can read it."),
    Line("rosa", "No, you can't."),
    Line("gary", "Still single?", gain=-3.0),
    Line("gary", "Don't ask. He gets sad."),
    Line("rosa", "Tell your brother I can read that."),
)
LAST = "Tell your brother I can read that."
TAIL = 1.0  # his frozen thumbs, held past a reading of the card that runs across the cut
CAPTION_MIN = 0.92  # every card and every page up past the 0.84 s reading minimum, with frames to spare
PAGE_MIN = 0.92
FIRST = LINES[0].text
LEAD = 1.3  # the read of the first line takes 0.96 s and the opening line needs 2.18 s up: he reads from here
PUSH = 1.06  # the silent lead-in moves: the first shot pushes in across it, as a first line would (L7, arm b)
BEATS, END = timed(
    LINES,
    (
        (LEAD, "gary", "", "side", "flat", "down"),  # her phone between them, her thumb going, his eyes on it
        (0.55, "gary", (0, 0, "Gary. Looks."), "side", "flat", "down"),  # he reads it out, flat
        (0.95, "gary", (0, 2, "Thin."), "side", "flat", "down", "reveal:thin"),
        (1.4, "rosa", 1, "half", "smug", "free"),  # not looking up
        (1.3, "gary", 2, "open", "flat", "down", "reveal:spoon"),
        (1.0, "rosa", 3, "half", "flat", "free", "reveal:insert"),  # the screen fills the frame
        (0.95, "rosa", "", "half", "flat", "free", "reveal:back"),  # and back to her, READ THIS
        (1.2, "rosa", "", "half", "flat", "free", "buzz"),  # the sister answers, on the cut to the screen
        (1.1, "gary", 4, "side", "flat", "down"),  # quieter
        (1.1, "gary", (5, 0, "Don't ask."), "side", "frown", "down", "reveal:corner"),
        (1.1, "gary", (5, 2, "He gets sad."), "sad", "frown", "down", "reveal:sad"),
        (0.55, "gary", "", "half", "flat", "hold", "reveal:own"),  # the hold: his phone comes up, away from her
        (0.95, "gary", "", "half", "flat", "free-right", "reveal:brent"),  # what he typed: his hand is the insert's
        (1.2, "rosa", "", "half", "flat", "free", "zoom"),  # the second hold: she types on, and the camera lands on her
        (1.3, "rosa", (6, 0, LAST), "half", "smug", "free"),
        (1.0, "gary", (6, 6, "that."), "wide", "flat", "hold", "sting"),  # the cut on "that", his thumbs stopped
    ),
    tail=TAIL,
)
# one card a line where a line is cut across beats, so no card is up for less than a reading
BEATS = [replace(b, caption=FIRST) if b.line == 0 else replace(b, caption=LAST) if b.line == 6 else b for b in BEATS]
SKETCH = replace(make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END), tail=TAIL, caption_min=CAPTION_MIN)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def _buzz(beats: Sequence[Beat]) -> float:
    return events(beats, "buzz")[0][0]


def pages(beats: Sequence[Beat]) -> tuple[tuple[float, str], ...]:
    """What Rosa's phone says and from when, on the beats of this build."""
    return (
        (0.0, "GARY LOOKS"),
        (_at(beats, "thin"), "THIN"),
        (_at(beats, "insert"), "HE CAN'T"),
        (_at(beats, "back"), "READ THIS"),
        (_buzz(beats), "STILL SINGLE?"),
        (_at(beats, "corner"), "DON'T ASK"),
        (max(_at(beats, "sad"), _at(beats, "corner") + PAGE_MIN), "HE GETS SAD"),
    )


def inserts(beats: Sequence[Beat]) -> list[tuple[float, float]]:
    """When her screen fills the frame: HE CAN'T, and STILL SINGLE? up to Gary's line. Refuses an order the recording
    broke."""
    out = [(_at(beats, "insert"), _at(beats, "back"))]
    after = next(b.start for b in beats if b.start > _buzz(beats) and b.who == "gary")
    out.append((_buzz(beats), after))
    if any(b <= a for a, b in out) or out[1][0] < out[0][1]:
        raise StagingError(f"{SLUG}: the inserts fell out of order on this recording: {out}")
    return out


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Both of them across the table, then each to one side of the frame, Rosa's side leaving room for her phone."""
    first = appearances(beats, end)[0]
    listening = {"start": 0.0, "eyes": "half", "mouth": "smug", "arms": "free"}
    still = {"start": 0.0, "eyes": "side", "mouth": "flat", "arms": "down"}
    lineup = Lineup(PLACES, {"gary": [still], "rosa": [listening]}, ((first.start, first.end),))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if lineup.staged(app):
            return lineup(cv, parent, app, mouths)
        fx, fy = collage.face(collage.LOOKS[app.who])
        poses = collage.parse_poses(app.poses, f"{app.who} at {app.start}")
        shift = ROSA_X if app.who == "rosa" else GARY_X
        moved = cv.group(parent, cv.uid("g"), x=shift)
        collage.DRAWERS[app.who](cv, moved, poses, app.end, (), enter=app.start, mouths=mouths.get(app.who, ()))
        return fx + shift, fy

    return draw


def _gated(cv, parent, spans: Sequence[tuple[float, float]]):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, list(spans))
    return g


def _tapping(cv, parent, start: float, stop: float):
    """A group its contents dip in, a tap at a time: the hand on the phone."""
    g = cv.group(parent, cv.uid("g"))
    period, depth = TAP
    taps = int((stop - start) / period)
    keys = [(round(start + i * period, 6), depth if i % 2 else 0.0) for i in range(taps + 1)]
    cv.keys(g, "y", keys, hold=False, local=False)
    return g


def _near_hand(cv, parent, who: str, side: int) -> None:
    """The hand of whoever holds a phone up at the eye, lower right of the insert."""
    k = NEAR_SCALE
    near = cv.group(parent, cv.uid("g"), scaleX=k, scaleY=k)
    frm, to = (NEAR_ELBOW[0] / k, NEAR_ELBOW[1] / k), (NEAR_HAND[0] / k, NEAR_HAND[1] / k)
    collage_everyday.arm(cv, near, who, frm, to, side=side)


def _two_shot(shot) -> None:
    """The opening: the table, the soup, and the phone at arm's length between their faces."""
    cv, app = shot.cv, shot.app
    collage_everyday.tablecloth(cv, shot.front, top=TWO_SHOT_TABLE)
    collage_everyday.food(cv, shot.front, "soup", SOUP[0], SOUP[1], SOUP[2])
    collage_big_type.big_type(cv, shot.front, **TWO_SHOT_PHONE, pages=pages(shot.beats))
    place = PLACES["rosa"]
    x, y = place.transform()
    near = cv.group(shot.front, cv.uid("g"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
    hand = ((TWO_SHOT_HAND[0] - x) / place.scale, (TWO_SHOT_HAND[1] - y) / place.scale)
    frm = collage_everyday.shoulder("rosa", -1)
    collage_everyday.arm(cv, _tapping(cv, near, app.start, app.end), "rosa", frm, hand, side=-1)


def _rosa(shot) -> None:
    """Her close: the phone beside her, her hand on it, and the same phone filling the frame in an insert."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    collage_everyday.tablecloth(cv, shot.front, top=TABLE)
    here = [(max(a, app.start), min(b, app.end)) for a, b in inserts(beats) if a < app.end and b > app.start]
    gaps, last = [], app.start
    for a, b in here:
        if a > last:
            gaps.append((last, a))
        last = b
    if last < app.end:
        gaps.append((last, app.end))
    if gaps:
        held = _gated(cv, shot.front, gaps)
        collage_big_type.big_type(cv, held, **ROSA_PHONE, pages=pages(beats))
        x, y = collage_everyday.shoulder("rosa", -1)
        collage_everyday.arm(cv, _tapping(cv, held, app.start, app.end), "rosa", (x + ROSA_X, y), ROSA_HAND, side=-1)
    if here:
        up = _gated(cv, shot.front, here)
        collage_big_type.big_type(cv, up, **INSERT, pages=pages(beats))
        _near_hand(cv, up, "rosa", -1)


def _gary(shot) -> None:
    """His close: the soup, her phone in the corner while he reads it out, then his own, and what he typed."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    own, brent = _at(beats, "own"), _at(beats, "brent")
    if app.end > own:  # drawn before the table, so it comes up from behind the edge
        rise = cv.group(shot.front, cv.uid("g"))
        cv.keys(rise, "y", [(own, OWN_DOWN), (own + OWN_RISE, OWN_UP)], kind="cubic-out", local=False)
        x = collage.CX + GARY_X - OWN_PHONE["w"] / 2
        collage_everyday.phone(cv, rise, x, 0.0, **OWN_PHONE, screen=BACK)
    collage_everyday.tablecloth(cv, shot.front, top=TABLE)
    collage_everyday.food(cv, shot.front, "soup", *GARY_SOUP)
    if app.start < own < app.end:
        reading = _gated(cv, shot.front, [(app.start, own)])
        collage_big_type.big_type(cv, reading, **CORNER_PHONE, pages=pages(beats))
        collage_everyday.arm(cv, reading, "rosa", CORNER_ELBOW, CORNER_HAND, side=-1)
    if app.start <= brent < app.end:
        up = _gated(cv, shot.front, [(brent, app.end)])
        collage_forecast.thread(
            cv,
            up,
            **INSERT,
            contact="BRENT",
            clock=((0.0, "DINNER"),),
            messages=(Message("MOM IS DOING IT AGAIN", brent, mine=True),),
        )
        _near_hand(cv, up, "gary", 1)


def dress(shot) -> None:
    if shot.app.start == 0.0:
        _two_shot(shot)
    else:
        (_rosa if shot.app.who == "rosa" else _gary)(shot)


def overlay(layer: Overlay) -> object:
    """The opening line, up from the first frame until the first line ends."""
    return opener.draw(
        layer.cv,
        layer.parent,
        TEXT,
        layer.first_line_end,
        measure=layer.measure,
        top=OPENER_TOP,
        names=NAMES,
        caption_top=UNDER_OPENER,
    )


def sounds(beats: Sequence[Beat], end: float) -> Sequence[Sound]:
    """Her taps under the opening and the insert, a clink on the bowl, and his fast small ones."""
    period = TAP[0] * 2
    typing = [a for a in appearances(beats, end) if a.who == "rosa" or a.start == 0.0]
    taps = tuple(round(a.start + i * period, 6) for a in typing for i in range(int((a.end - a.start) / period) + 1))
    own, brent = _at(beats, "own"), _at(beats, "brent")
    small = tuple(round(own + i * SMALL_TAPS, 6) for i in range(int((brent + 0.5 - own) / SMALL_TAPS)))
    return (
        Sound("taps", foley.KEYS, taps, TAP_GAIN),
        Sound("small", foley.KEYS, small, TAP_GAIN - 3.0),
        Sound("spoon", foley.CLINK, (_at(beats, "spoon"),), SPOON_GAIN),
    )


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"rosa": ROOM, "gary": ROOM},
    dress=dress,
    cast=casting,
    bleed=True,
    first_shot_push=PUSH,
    keep_signature=True,
    sounds=sounds,
    bitrate=BITRATE,
    keyframes=KEYFRAMES,
    bframes=0,
    loudness="-14",
    sentence_rows=True,
    overlay=overlay,
    caption_tops={FIRST: UNDER_OPENER},
    clear_bug=True,
)
