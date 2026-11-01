"""Cold Front — the sketch as data: first frost tonight, exes moving in. Omar reads it off a paper map; Deb, under her
duvet with Priya on speaker, says not mine. Scattered hellos by nine, and at nine one lands. Priya asks if he texted.
No. The second bubble lands on Omar's last word. He's changed. Priya and Omar say her name on one beat, and she answers
anyway.
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
OVERLAY = "FIRST COLD NIGHT"
CHYRON = dict(x=110.0, y=1660.0, w=860, h=130)
OMAR_X = -130.0  # his side of the frame, the map on the other
OMAR_HAND = (748.0, 1150.0)  # on the map's edge, where his eyes go when they go sideways
OMAR_SCALES = (1.0, 1.0, 1.2, 1.32, 1.4)  # one per appearance of his: closer each time the forecast gets personal
DEB_X = -150.0  # her side of the frame, the phone on the other
DEB_SCALES = {"insert": 1.0, "wide": 1.0, "close": 1.14}
PHONE = dict(x=618.0, y=1130.0, w=372.0, h=640.0)  # in her hand, its screen toward us
INSERT = dict(x=150.0, y=790.0, w=780.0, h=1090.0)  # clear of the shelf above and of the pill
BUBBLE_AT = (712.0, 1338.0)  # where her thumb covers the first bubble on the phone in her hand
ELBOW = (654.0, 1740.0)  # under the duvet, so the forearm rises out of it beside the phone
HAND_REST = (640.0, 1570.0)  # her hand at the phone's foot, off its words
HAND_ABOVE = (625.0, 1565.0)  # the thumb lifts
HAND_DOWN = (635.0, 1590.0)  # and comes down
HAND_MOVE = 0.35  # seconds the hand takes to move
INSERT_HAND_SCALE = 1.9  # the phone is up at the eye, so her hand is near as well
INSERT_HAND = (936.0, 1632.0)
INSERT_ELBOW = (1120.0, 2040.0)
DUVET_TOP = 1600.0
DUVET_UP = 80.0  # how far she pulls it up on the last word
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
_BEATS, END = timed(
    LINES,
    (
        (2.7, "omar", 0, "side", "flat", "free-right"),  # the arrow slides from frame one, his hand on the map
        (0.9, "deb", 1, "open", "smile", "free-right"),  # at the TV, nothing to fear
        (1.1, "omar", 2, "side", "flat", "free-right", "reveal:clock"),
        (0.85, "deb", LINES[2].text, "side", "smile", "free-right", "reveal:insert"),  # cut on "nine": still 8:59
        (0.95, "deb", "", "side", "smile", "free-right", "buzz"),  # 9:00, and the first bubble
        (0.4, "deb", "", "side", "smile", "free-right", "reveal:cover"),  # the smile stays, her thumb goes over it
        (1.0, "deb", 3, "side", "smile", "free-right"),
        (0.95, "deb", 4, "side", "smile", "free-right"),  # eyes on the phone
        (2.6, "omar", 5, "side", "flat", "free-right"),
        (0.7, "deb", LINES[5].text, "side", "smile", "free-right", "buzz"),  # the cut lands on his last word
        (0.85, "deb", 6, "sad", "smile", "free-right"),  # softly
        (0.8, "omar", 7, "open", "flat", "down"),  # his eyes come off the map, to the lens
        (0.5, "deb", "", "up", "smile", "free-right", "reveal:tv"),  # she looks up at the TV
        (0.35, "deb", "", "side", "smile", "free-right"),  # and down, and the smile has not moved
        (0.87, "deb", "", "side", "smile", "free-right", "reveal:answer"),  # her thumb comes down: the green bubble
        (1.2, "omar", (9, 0, "He doesn't miss you."), "open", "flat", "down"),
        (0.6, "deb", (9, 4, "He's cold."), "open", "smile", "free-right", "reveal:duvet"),
    ),
    tail=0.45,
)
# two cuts land on a line's last word, its caption still up: to the phone on "nine", and the second bubble on "myself"
_LANDS = {
    next(i for i, b in enumerate(_BEATS) if b.caption == LINES[n].text and b.who == "deb"): (n, word)
    for n, word in ((2, 3), (5, 6))
}
BEATS = [replace(b, line=_LANDS[i][0], word=_LANDS[i][1]) if i in _LANDS else b for i, b in enumerate(_BEATS)]
SKETCH = replace(make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END), tail=0.45)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def inserts(beats: Sequence[Beat]) -> list[tuple[float, float]]:
    """When the phone fills the frame: from the top bar's last minute to the cover, from the second bubble to the next
    line, and from the green bubble to Omar. Refuses an order the recording broke."""
    second = events(beats, "buzz")[1][0]
    next_line = next(b.start for b in beats if b.start > second and b.line is not None and b.word == 0)
    out = [(_at(beats, "insert"), _at(beats, "cover")), (second, next_line)]
    answer = _at(beats, "answer")
    out.append((answer, next(b.start for b in beats if b.start > answer)))
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


def _thread(cv, parent, box: dict, beats: Sequence[Beat]) -> None:
    buzzes = [t for t, _ in events(beats, "buzz")]
    collage_forecast.thread(
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
    collage_forecast.weather_map(cv, shot.back, **MAP, arrow=arrow, slide=slide, clock=clock)
    if any(p["arms"] == "free-right" for p in app.poses):
        x, y = collage_everyday.shoulder("omar", 1)
        collage_everyday.arm(cv, shot.front, "omar", (x + OMAR_X, y), OMAR_HAND, side=1)
    if n < 2:
        collage_sets.sign(cv, shot.front, OVERLAY, **CHYRON, size=74, fill="#ffd166", tilt=-1)


def _hand(beats: Sequence[Beat]):
    """Where her hand is at a second, and the seconds to key it at."""
    cover = _at(beats, "cover")
    changed = next(b.start for b in beats if b.line == 6)
    answer = _at(beats, "answer")
    keys = [
        (0.0, HAND_REST),
        (cover, HAND_REST),
        (cover + HAND_MOVE, BUBBLE_AT),
        (changed, BUBBLE_AT),
        (changed + HAND_MOVE, HAND_ABOVE),
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
    _thread(cv, _gated(cv, shot.front, gaps) if gaps else shot.front, PHONE, shot.beats)
    if not gaps:
        raise StagingError(f"{SLUG}: the shot at {app.start} s is all insert")
    where, times = _hand(shot.beats)
    collage_everyday.reach(
        cv, _gated(cv, shot.front, gaps), "deb", ELBOW, where, [t for t in times if t <= shot.end] + [shot.end], side=1
    )
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
    sounds=sounds,
    bitrate=BITRATE,
    keyframes=KEYFRAMES,
    bframes=0,
    loudness="-14",
    sentence_rows=True,
)
