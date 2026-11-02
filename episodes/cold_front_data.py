"""Cold Front — the sketch as data: first frost tonight, exes moving in. Omar reads it off a paper map; Deb, under her
duvet with Priya on speaker, says not mine. Scattered hellos by nine, and at nine one lands. Priya asks if he texted,
and her thumb slides over it. No. Omar reads the second bubble out before it lands; it lands on the cut to the phone.
He's changed. Priya and Omar say her name on one beat, and she answers anyway.
"He doesn't miss you. He's cold."

Collage style (ADR 0026), Okayville batch E on the send test: the recipient is your best friend, the one who always
answers him. The Collage busts free one arm at a time, so Deb's hand stays on her phone and the hand to her chest in the
script's beat 9 is played in the eyes. ElevenLabs premade voices, lip-synced; Priya is a voice on the phone, no face.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from srstudio import camera, collage, collage_everyday, collage_forecast, collage_sets, foley
from srstudio.collage_forecast import Message
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances, events
from srstudio.staging import StagingError

SEED = 3505
SLUG = "cold-front"
TITLE = "Cold Front — Omar, Deb and Priya (Collage)"
NAMES = ("omar", "deb", "priya")
NEWS = "newsroom"
HOME = "living-room"
DESCRIPTION = (
    "A Collage sketch: on the first cold night an anchor forecasts exes moving in, and at home a woman who says not "
    "hers answers one anyway."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a news anchor with a moustache stands beside a paper weather map with a big blue arrow "
    "lettered EXES. A woman under a duvet at home holds a phone on a call. Grey message bubbles land "
    "on the phone from a contact named DON'T, and she answers with a green one. Lines appear in tinted pills."
)
NARRATION = (
    f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesized phone buzzes, a paper slide, a room hush "
    "and a small pop."
)
NOTE = "ElevenLabs premade voices Daniel, Jessica and Sarah at their natural pace; no reference-voice cloning."

MAP = dict(x=590.0, y=560.0, w=450.0, h=640.0)
ZOOM_MAP_Y = 775.0  # hung lower in the shot that crash zooms: the snap carries the map up, and it stops under the bug
OVERLAY = "FIRST COLD NIGHT"
CHYRON = dict(x=110.0, y=1660.0, w=860, h=130)
OMAR_X = -130.0  # his side of the frame, the map on the other
OMAR_HAND = (748.0, 1150.0)  # on the map's edge, where his eyes go when they go sideways
OMAR_SCALES = (1.0, 1.0, 1.2, 1.0, 1.4)  # one per appearance, closer as it gets personal; the fourth crash zooms
DEB_X = -150.0  # her side of the frame, the phone on the other
DEB_SCALES = {"insert": 1.0, "wide": 1.0, "close": 1.14}
PHONE = dict(x=618.0, y=1130.0, w=372.0, h=640.0)  # in her hand, its screen toward us
INSERT = dict(x=150.0, y=790.0, w=780.0, h=1090.0)  # clear of the shelf above and of the pill
BUBBLE_AT = (712.0, 1338.0)  # where her thumb covers the first bubble on the phone in her hand
ELBOW = (654.0, 1740.0)  # under the duvet, so the forearm rises out of it beside the phone
HAND_REST = (630.0, 1500.0)  # her hand on the phone's edge, off its words, the forearm in sight above the duvet
HAND_ABOVE = (625.0, 1475.0)  # the thumb lifts
HAND_DOWN = (636.0, 1500.0)  # and comes down
HAND_MOVE = 0.35  # seconds the hand takes to move
HEY_HELD = 0.9  # seconds HEY stays readable on the phone in her hand, past the check's 0.84, before her thumb is on it
OVER_HEY = 0.85  # how far through its move the hand has the word covered, when the word goes
INSERT_HAND_SCALE = 1.9  # the phone is up at the eye, so her hand is near as well
INSERT_HAND = (936.0, 1632.0)
INSERT_ELBOW = (1120.0, 2040.0)
DUVET_TOP = 1600.0
DUVET_UP = 55.0  # how far she pulls it up on the last word
LAST_LINE_FOOT = 1522.0  # the foot of MYSELF. on the phone in her hand, in the shot's units: the pull stops under it
DUVET_PULL = 0.42
DUVET = "#7a6f9b"
EVENING = "#2b2a55"
SHELF_TOP = 580.0  # the wash over her wall stops here, above the cactus
ARROW_SLIDE = 1.5  # seconds the arrow slides down the map, from the first frame
EIGHT_59, NINE = "8:59", "9:00"
BITRATE = 5_800_000  # bits a second: the grain, new every frame, otherwise costs the size; encoded in software
KEYFRAMES = 7.0  # with no B frames, the grain leaves x264 its cuts (ADR 0083)

LINES = (
    Line("omar", "First frost tonight. Exes are moving in."),
    Line("deb", "Not mine."),
    Line("omar", "Scattered hellos by nine."),
    Line("priya", "Did he text?", phone=True),
    Line("deb", "No."),
    Line("omar", "Tonight's low: 'I've been working on myself.'"),
    Line("deb", "He's changed."),
    Line("omar", "Deb."),
    Line("priya", "Deb.", phone=True, together=True),
    Line("omar", "He doesn't miss you. He's cold."),
)
BEATS, END = timed(
    LINES,
    (
        (1.4, "omar", (0, 0, "First frost tonight."), "side", "flat", "free-right"),  # the arrow slides from frame one
        (1.3, "omar", (0, 3, "Exes are moving in."), "open", "flat", "free-right"),  # his eyes and a new card on "Exes"
        (0.9, "deb", 1, "open", "smile", "free-right"),  # at the TV, nothing to fear
        (1.95, "omar", 2, "side", "flat", "free-right", "reveal:clock"),  # held to the end of his caption
        (1.0, "deb", "", "side", "smile", "free-right", "buzz"),  # the cut lands at 9:00 with the first bubble
        (1.0, "deb", 3, "side", "smile", "free-right", "reveal:cover"),  # back to her on Priya's first word
        (0.95, "deb", 4, "side", "smile", "free-right"),  # eyes on the phone
        (3.3, "omar", 5, "side", "flat", "free-right"),  # held to the end of his caption
        (0.85, "deb", "", "side", "smile", "free-right", "buzz"),  # the cut lands with the bubble he just read out
        (0.85, "deb", 6, "sad", "smile", "free-right"),  # softly
        (0.85, "omar", 7, "open", "flat", "down", "zoom"),  # his eyes off the map, and the crash zoom on her name
        (0.33, "deb", "", "side", "smile", "free-right", "reveal:phone"),  # straight to the phone, and nothing yet
        (0.15, "deb", "", "side", "smile", "free-right", "reveal:answer"),  # her thumb comes down: the green bubble
        (0.7, "deb", "", "side", "smile", "free-right", "sting"),  # and the two sagging notes under it
        (1.2, "omar", (9, 0, "He doesn't miss you."), "open", "flat", "down"),
        (0.6, "deb", (9, 4, "He's cold."), "open", "smile", "free-right", "reveal:duvet"),
    ),
    tail=0.45,
)
SKETCH = replace(make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END), tail=0.45)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def inserts(beats: Sequence[Beat]) -> list[tuple[float, float]]:
    """When the phone fills the frame: from the first bubble to the cover, from the second to the next line, and from
    the cut back to it, just before the green bubble, to Omar. Refuses an order the recording broke."""
    first, second = [t for t, _ in events(beats, "buzz")][:2]
    next_line = next(b.start for b in beats if b.start > second and b.line is not None and b.word == 0)
    out = [(first, _at(beats, "cover")), (second, next_line)]
    answer = _at(beats, "answer")
    out.append((_at(beats, "phone"), next(b.start for b in beats if b.start > answer and b.line is not None)))
    if any(b <= a for a, b in out) or any(c[0] < p[1] for p, c in zip(out, out[1:], strict=False)):
        raise StagingError(f"{SLUG}: the inserts fell out of order on this recording: {out}")
    return out


def _omar_shot(beats: Sequence[Beat], end: float, app: Appearance) -> int:
    shots = [a.start for a in appearances(beats, end) if a.who == "omar"]
    return shots.index(app.start)


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Omar to one side of his map, closer each time; Deb to one side of her phone, full size under each insert."""
    spans = inserts(beats)
    cover = _at(beats, "cover")

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        fx, fy = collage.face(collage.LOOKS[app.who])
        poses = collage.parse_poses(app.poses, f"{app.who} at {app.start}")
        shift = OMAR_X if app.who == "omar" else DEB_X
        moved = cv.group(parent, cv.uid("g"), x=shift)
        collage.DRAWERS[app.who](cv, moved, poses, app.end, (), enter=app.start, mouths=mouths.get(app.who, ()))
        face = (fx + shift, fy)
        if app.who == "omar":
            k = OMAR_SCALES[_omar_shot(beats, end, app)]
            if k > 1:
                camera.anchor(parent, *collage_sets.zoom_pivot(NEWS, face, k, height=1920.0), place=True)
                parent.scaleX = parent.scaleY = k
            return face
        k = DEB_SCALES["close"]
        camera.anchor(parent, *collage_sets.zoom_pivot(HOME, face, k), place=True)
        keys = [(app.start, k if app.start >= cover else DEB_SCALES["wide"])]
        for a, b in spans:
            if a == app.start:
                keys = [(a, DEB_SCALES["insert"])]  # a shot that opens on the phone opens at the phone's size
            elif app.start < a < app.end:
                keys.append((a, DEB_SCALES["insert"]))
            if app.start < b < app.end:
                keys.append((b, k))
        camera.zoom_holds(cv, parent, sorted(set(keys)))
        return face

    return draw


def _gated(cv, parent, spans: Sequence[tuple[float, float]]):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, list(spans))
    return g


def _thread(cv, parent, box: dict, beats: Sequence[Beat]):
    buzzes = [t for t, _ in events(beats, "buzz")]
    return collage_forecast.thread(
        cv,
        parent,
        **box,
        contact="DON'T",
        call="PRIYA",
        clock=((0.0, EIGHT_59), (buzzes[0], NINE)),
        messages=(
            Message("HEY", buzzes[0]),
            Message("I'VE BEEN WORKING ON MYSELF.", buzzes[1]),
            Message("HEY", _at(beats, "answer"), mine=True),
        ),
    )


def _news(shot) -> None:
    """The map behind him, its arrow sliding on the first shot; the clock card from the second; the overlay on both."""
    cv, app = shot.cv, shot.app
    n = _omar_shot(shot.beats, shot.end, app)
    clock = (EIGHT_59, (0.0, collage_forecast.FOREVER)) if n == 1 else None  # closer, the frame would cut it
    slide = (0.0, ARROW_SLIDE) if n == 0 else None
    arrow = "EXES" if n < 3 else ""  # a close framing would cut the word
    box = {**MAP, "y": ZOOM_MAP_Y} if OMAR_SCALES[n] == 1.0 and n > 1 else MAP
    collage_forecast.weather_map(cv, shot.back, **box, arrow=arrow, slide=slide, clock=clock)
    if any(p["arms"] == "free-right" for p in app.poses):
        x, y = collage_everyday.shoulder("omar", 1)
        collage_everyday.arm(cv, shot.front, "omar", (x + OMAR_X, y), OMAR_HAND, side=1)
    if n < 2:
        collage_sets.sign(cv, shot.front, OVERLAY, **CHYRON, size=74, fill="#ffd166", tilt=-1)


def _thumb(beats: Sequence[Beat]) -> float:
    """When her hand starts for the bubble: back from the insert HEY is read, and it goes as Priya asks."""
    return _at(beats, "cover") + HEY_HELD - OVER_HEY * HAND_MOVE


def _covered(beats: Sequence[Beat]) -> float:
    """When her fist has the first HEY covered, which is when the word stops being drawn under it."""
    return _thumb(beats) + OVER_HEY * HAND_MOVE


def _hide(cv, phone, words: str, until: float, last: bool = False) -> None:
    """The bubble ``words`` on a drawn ``phone`` stops at ``until``, its paper left: the first such bubble, or the
    ``last``. The thread is an approved part with no such option, so the layer it drew is gated from here."""
    texts = {a.id for a in cv.assets.iter() if a.xml_name == "text" and a.text == words}
    layers = [n for n in phone.iter() if n.xml_name == "layer" and n.asset in texts]
    cv.gate(layers[-1 if last else 0], [(0.0, until)])


def _hand(beats: Sequence[Beat]):
    """Where her hand is at a second, and the seconds to key it at. It leaves the first bubble under the second's
    insert, so she is back with the hand clear of the words and the arm in sight for the whole of her line."""
    thumb = _thumb(beats)
    second = events(beats, "buzz")[1][0]
    answer = _at(beats, "answer")
    keys = [
        (0.0, HAND_REST),
        (thumb, HAND_REST),
        (thumb + HAND_MOVE, BUBBLE_AT),
        (second, BUBBLE_AT),
        (second + HAND_MOVE, HAND_ABOVE),
        (answer - 0.15, HAND_ABOVE),
        (answer, HAND_DOWN),
    ]

    def where(t: float):
        for (a, p), (b, q) in zip(keys, keys[1:], strict=False):
            if a <= t <= b and b > a:
                u = (t - a) / (b - a)
                return (p[0] + u * (q[0] - p[0]), p[1] + u * (q[1] - p[1]))
        return keys[-1][1]

    return where, [t for t, _ in keys]


def _sofa(shot) -> None:
    """Her night: the room dimmed under the shelf, the phone in her hand, her forearm up from the duvet; and
    the same phone filling the frame in each insert."""
    cv, app = shot.cv, shot.app
    above = cv.grad("cold-above", [(0, EVENING + "cc"), (1, EVENING + "00")], (0, 0, 0, 1))
    cv.rect(shot.back, 0, 0, cv.width, SHELF_TOP, above)
    wash = cv.grad("cold-wash", [(0, EVENING + "00"), (0.12, EVENING + "99"), (1, EVENING + "cc")], (0, 0, 0, 1))
    cv.rect(shot.back, 0, 770, cv.width, 1150, wash)
    spans = inserts(shot.beats)
    insert_here = [(max(a, app.start), min(b, app.end)) for a, b in spans if a < app.end and b > app.start]
    gaps, last = [], app.start
    for a, b in insert_here:
        if a > last:
            gaps.append((last, a))
        last = b
    if last < app.end:
        gaps.append((last, app.end))
    if gaps:  # the last of the three shots of the phone is the phone from cut to cut
        phone = _thread(cv, _gated(cv, shot.front, gaps), PHONE, shot.beats)
        covered = _covered(shot.beats)
        if app.start <= covered < app.end:
            _hide(cv, phone, "HEY", covered)
        _hide(cv, phone, "HEY", _at(shot.beats, "answer"), last=True)  # her reply lands under the duvet, unseen here
        where, times = _hand(shot.beats)
        keys = [t for t in times if t <= shot.end] + [shot.end]
        collage_everyday.reach(cv, _gated(cv, shot.front, gaps), "deb", ELBOW, where, keys, side=1)
    pull = cv.group(shot.front, cv.uid("g"))
    pulled = _at(shot.beats, "duvet")
    cv.keys(pull, "y", [(pulled, 0.0), (pulled + DUVET_PULL, -DUVET_UP)], kind="cubic-out", local=False)
    collage_everyday.duvet(cv, pull, top=DUVET_TOP, colour=DUVET)
    if insert_here:
        up = _gated(cv, shot.front, insert_here)
        _thread(cv, up, INSERT, shot.beats)
        k = INSERT_HAND_SCALE
        near = cv.group(up, cv.uid("g"), scaleX=k, scaleY=k)
        frm, to = (INSERT_ELBOW[0] / k, INSERT_ELBOW[1] / k), (INSERT_HAND[0] / k, INSERT_HAND[1] / k)
        collage_everyday.arm(cv, near, "deb", frm, to, side=-1)  # her own hand, seen from her side: thumb to the phone


def dress(shot) -> None:
    (_news if shot.app.who == "omar" else _sofa)(shot)


def sounds(beats: Sequence[Beat], end: float) -> Sequence[Sound]:
    """Paper on the map, the room behind her, a small pop as she answers."""
    homes = [a.start for a in appearances(beats, end) if a.who == "deb"]
    return (
        Sound("slide", foley.SCRAPE, (0.0,), -9.0),
        Sound("hush", foley.HUM, (homes[0], homes[-2]), -26.0),
        Sound("pop", foley.CHIRP, (_at(beats, "answer"),), -11.0),
    )


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"omar": NEWS, "deb": HOME},
    dress=dress,
    cast=casting,
    bleed=True,
    keep_signature=True,
    sounds=sounds,
    bitrate=BITRATE,
    keyframes=KEYFRAMES,
    bframes=0,
    loudness="-14",
    sentence_rows=True,
)
