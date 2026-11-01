"""Thought of You — the sketch as data: one in the morning, and Gary's phone buzzes on his chest. His mother has sent
an article, no comment, then another: houseplants, kidneys, his sofa, each worse than the last. "Just thought of you."
Then the fourth: LOCAL MAN HAS NOT CALLED HIS MOTHER. "Mom. You wrote this." She turns her cup on its saucer. "His poor
mother." She looks up, pleasant, done. "Saw it and thought of you." On his end, one more buzz.

Collage style (ADR 0026), Okayville batch E on the send test: the recipient is your mom, and sending this reel is the
gesture the reel is about. Gary is Rosa's son, as in best-angle and the-will. The Collage busts have no lying pose, so
Gary sits up in bed against the headboard, sunk in the duvet. Rosa has no cup pose, so her cup is heard and not seen.
ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from srstudio import camera, collage, collage_article, collage_everyday, collage_photo, collage_sets, foley
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Sound, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events
from srstudio.staging import StagingError

SEED = 3407
SLUG = "thought-of-you"
TITLE = "Thought of You — Gary and Rosa (Collage)"
NAMES = ("gary", "rosa")
BED = "bedroom"
HOME = "living-room"
DESCRIPTION = (
    "A Collage sketch: at one in the morning a mother sends her son articles with no comment, each worse than the "
    "last, until the headline is about him."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a balding man sits up in bed in the dark, lit by his phone. His mother, an older woman "
    "in pearls, sits in her living room with her phone. Four headlines fill the screen in turn, the last reading LOCAL "
    "MAN HAS NOT CALLED HIS MOTHER. Lines appear in tinted pills."
)
NARRATION = (
    f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized phone buzz, a sip, a cup on its "
    "saucer, a whoosh and a sting."
)
NOTE = "ElevenLabs premade voices Chris and Matilda at their natural pace; no reference-voice cloning."

HEADLINES = (
    "TEN HOUSEPLANTS SLOWLY KILLING YOU",
    "YOUR KIDNEYS: NINE SILENT WARNINGS",
    "IS YOUR SOFA MAKING YOU SAD?",
    "LOCAL MAN HAS NOT CALLED HIS MOTHER",
)
HOUR = "1:04"
GARY_AT = (100.0, 110.0)  # right of the frame's centre, so a zoom that keeps the shelf keeps his face; down in the bed
RISE = (150.0, 0.5)  # the opening: how much lower he starts, and the seconds his face takes to come up into the light
INSERT = dict(x=190.0, y=830.0, w=700.0, h=960.0)  # clear of the shelf above, and of the pill
INSERT_FOOT = 1790.0  # the slow push grows the phone from here, so its top stays under the shelf
SLIDE = (1120.0, 0.2)  # the phone comes up from this far below, in these seconds
READ = 1.3  # seconds a headline holds, at the least: the floor of reading it
BACK = (0.0, 0.0, 0.9)  # seconds of his face before the cut to her, per headline: only the third gives him the clock
REVEAL_PUSH = 1.05
HER_PUSH = (1.18, 1.2)  # the push to a close on her last look: the scale, and the seconds it takes
HELD = dict(x=435.0, y=1400.0, w=210.0, h=340.0)  # a phone in both hands, seen from the back
HELD_GARY_X = 535.0
HOLDING = "free"  # Gary's screen-left arm is the shot's, so that it can hold the phone where the zoom still shows it
ELBOW_GARY = (450.0, 1660.0)  # under the duvet
HAND_GARY = (HELD_GARY_X + 4.0, 1555.0)  # above the duvet, and inside the frame at the zoom's scale
INSERT_HAND_SCALE = 2.0  # the phone is up at the eye, so the hand holding it is near as well
INSERT_HAND = (892.0, 1500.0)  # on the phone's right edge: his thumb lies on the page, clear of the words
INSERT_ELBOW = (1010.0, 2010.0)  # past the foot of the frame, so the arm stays on through the phone's slide
FROM_CARD = dict(x=70.0, y=560.0, w=430, h=120)
ZOOMED_CAPTION_TOP = 1570.0  # his line is under the zoom, where the usual place is the cactus's
CLOCK = dict(x=790.0, y=1510.0, w=250.0)  # in the near plane, where his eyes go when they go sideways
NIGHT = "#141a3a"
EVENING = "#2b1a3a"
GLOW = "#9fc5ff"
LAMP = "#ffc66b"
SHELF_TOP = 580.0  # the wash over her wall stops here, above the cactus
BITRATE = 5_800_000  # bits a second: the grain, new every frame, otherwise costs 56 MB here; encoded in software
# At the defaults the grain keeps x264 from keying this reel's cuts; this interval with no B frames lands all of them
KEYFRAMES = 7.0
HOLD_FOR_THE_WORD = 0.9  # the cup meets the saucer on the beat before the line

LINES = (
    Line("gary", "Mom, what is this?"),
    Line("rosa", "Just thought of you."),
    Line("gary", "I don't own a plant."),
    Line("rosa", "That's how it starts."),
    Line("gary", "Why kidneys?"),
    Line("rosa", "You looked exhausted at Easter."),
    Line("gary", "Mom, it's one in the morning."),
    Line("rosa", "I'm up."),
    Line("gary", "Mom. You wrote this."),
    Line("rosa", "His poor mother."),
    Line("rosa", "Saw it and thought of you."),
)
BEATS, END = timed(
    LINES,
    (
        (1.8, "gary", 0, "wide", "frown", HOLDING, "buzz"),  # the phone lights his face, already asking
        (1.4, "rosa", 1, "half", "smile", "hold"),  # no hurry
        (0.45, "gary", "", "open", "flat", HOLDING, "buzz"),  # the first headline, before his line
        (1.55, "gary", 2, "half", "frown", HOLDING),
        (1.3, "rosa", 3, "half", "flat", "hold"),
        (0.45, "gary", "", "open", "flat", HOLDING, "buzz"),
        (1.05, "gary", 4, "wide", "frown", HOLDING),
        (0.5, "rosa", "", "half", "flat", "hold", "reveal:sip"),  # heard; she has not looked up
        (1.6, "rosa", 5, "open", "flat", "hold"),
        (0.45, "gary", "", "open", "flat", HOLDING, "buzz"),
        (2.2, "gary", 6, "side", "frown", HOLDING),  # he looks at the clock, and it stays up long enough to read
        (0.8, "rosa", 7, "open", "smile", "hold"),
        (1.7, "gary", "", "open", "flat", HOLDING, "buzz"),  # the reveal: the buzz, then silence, the phone pushing in
        (0.2, "gary", "", "wide", "flat", HOLDING, "zoom"),  # back on his face: he has read it
        (0.7, "gary", "", "wide", "flat", HOLDING, "sting"),  # very still
        (1.9, "gary", 8, "half", "flat", HOLDING),
        (1.4, "rosa", "", "half", "flat", "hold", "reveal:saucer"),  # the cup on its saucer, a quarter turn, heard
        (1.2, "rosa", 9, "half", "frown", "hold"),
        (1.2, "rosa", "", "open", "flat", "hold", "reveal:push"),  # she looks up, into the phone, at him
        (1.7, "rosa", 10, "open", "smile", "hold"),  # pleasant, done
        (0.0, "rosa", "", "open", "smile", "hold", "buzz"),  # on his end
    ),
    tail=0.4,
)
SKETCH = replace(make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END), tail=0.4)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Gary sat up in bed, right of center; Rosa on her sofa, and the push onto her last look."""
    push = _at(beats, "push")

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        fx, fy = collage.face(collage.LOOKS[app.who])
        poses = collage.parse_poses(app.poses, f"{app.who} at {app.start}")
        if app.who == "gary":
            x, y = GARY_AT
            moved = cv.group(parent, cv.uid("g"), x=x, y=y)
            if app.start == 0.0:
                cv.keys(moved, "y", [(0.0, y + RISE[0]), (RISE[1], y)], kind="cubic-out", local=False)
            collage.DRAWERS["gary"](
                cv, moved, poses, app.end, (), enter=app.start, mouths=mouths.get("gary", ())
            )  # fmt: skip
            return collage_sets.zoom_pivot(BED, (fx + x, fy + y), ZOOM_SCALE)
        collage.DRAWERS["rosa"](cv, parent, poses, app.end, (), enter=app.start, mouths=mouths.get("rosa", ()))
        if app.start <= push < app.end:
            scale, seconds = HER_PUSH
            camera.anchor(parent, *collage_sets.zoom_pivot(HOME, (fx, fy), scale), place=True)
            camera.push_in(cv, parent, scale=[(push, 1.0), (push + seconds, scale)])
        return fx, fy

    return draw


def _gated(cv, parent, a: float, b: float):
    g = cv.group(parent, cv.uid("g"))
    cv.gate(g, [(a, b)])
    return g


def spans(beats: Sequence[Beat]) -> list[tuple[float, float]]:
    """When each headline is up: from its buzz until the cut to her, less :data:`BACK`, or the zoom for the last one,
    whose silence is the reveal. Refuses a headline that would not hold long enough to read."""
    buzzes = [t for t, _ in events(beats, "buzz")][1 : 1 + len(HEADLINES)]
    zoom = events(beats, "zoom")[0][0]
    cuts = [b.start for b in beats if b.who == "rosa"]
    out = []
    for i, at in enumerate(buzzes):
        cut = next(t for t in cuts if t > at)
        stop = zoom if i == len(HEADLINES) - 1 else cut - BACK[i]
        if round(stop - at, 6) < READ or stop > cut:
            raise StagingError(f"{SLUG}: the headline at {at} s holds {stop - at:.2f} s before the cut at {cut} s")
        out.append((at, stop))
    return out


def _insert(shot, at: float, stop: float, headline: str, last: bool) -> None:
    """The phone up to the viewer's eye, sliding in on its buzz; the last one pushes slowly in through its silence."""
    cv = shot.cv
    shown = _gated(cv, shot.front, at, stop)
    slid = cv.group(shown, cv.uid("g"))
    cv.keys(slid, "y", [(at, SLIDE[0]), (at + SLIDE[1], 0.0)], kind="cubic-out", local=False)
    pushed = cv.group(slid, cv.uid("g"))  # a group of its own: the anchor would take the slide's keys
    if last:
        camera.anchor(pushed, 540.0, INSERT_FOOT, place=True)
        camera.push_in(cv, pushed, scale=[(at + SLIDE[1], 1.0), (stop, REVEAL_PUSH)])
    collage_article.article(cv, pushed, **INSERT, headline=headline, sender="FROM: MOM")
    k = INSERT_HAND_SCALE
    near = cv.group(pushed, cv.uid("g"), scaleX=k, scaleY=k)
    frm, to = (INSERT_ELBOW[0] / k, INSERT_ELBOW[1] / k), (INSERT_HAND[0] / k, INSERT_HAND[1] / k)
    collage_everyday.arm(cv, near, "gary", frm, to, side=1)


def _bed(shot) -> None:
    """The dark behind him and on the duvet, the phone's light on his face, the phone, the clock, the headlines."""
    cv, app = shot.cv, shot.app
    dark = cv.grad("collage-thought-dark", [(0, NIGHT + "00"), (0.2, NIGHT + "99"), (1, NIGHT + "cc")], (0, 0, 0, 1))
    cv.rect(shot.back, 0, 790, cv.width, 1130, dark)  # behind him: he sits in the phone's light
    phone_at = HELD | {"x": HELD_GARY_X, "y": HELD["y"] + GARY_AT[1] - 40.0}
    held = cv.group(shot.front, cv.uid("g"))
    if app.start == 0.0:  # it comes up with him, or his chin would land on it
        cv.keys(held, "y", [(0.0, RISE[0]), (RISE[1], 0.0)], kind="cubic-out", local=False)
    collage_everyday.phone(cv, held, **phone_at, screen="#23202b")
    x, y = collage_everyday.shoulder("gary")
    collage_everyday.arm(cv, held, "gary", (x + GARY_AT[0], y + GARY_AT[1]), ELBOW_GARY, hand=False)
    collage_everyday.arm(cv, held, "gary", ELBOW_GARY, HAND_GARY, side=-1)
    collage_everyday.duvet(cv, shot.front)
    hem = cv.grad("collage-thought-hem", [(0, NIGHT + "00"), (1, NIGHT + "bb")], (0, 0, 0, 1))
    cv.rect(shot.front, 0, 1600, cv.width, 320, hem)
    glow = cv.rgrad("collage-thought-glow", [(0, GLOW + "55"), (1, GLOW + "00")])
    light = cv.group(shot.front, cv.uid("g"))
    cv.rect(light, 90, 1050, 900, 620, glow)
    if app.start == 0.0:
        cv.keys(light, "opacity", [(0.0, 0.0), (RISE[1], 1.0)], hold=False, local=False)
    night = cv.group(shot.front, cv.uid("g"))
    cv.rect(night, CLOCK["x"] - 26, CLOCK["y"] + 118, 330, 330, "#2d2048", collage.INK, 6)  # the nightstand
    headlines = spans(shot.beats)
    shown, last_stop = [], app.start
    for at, stop in headlines:  # off behind a headline, where the phone would leave a sliver of its digits
        if app.start <= at < app.end:
            shown.append((last_stop, at))
            last_stop = stop
    if last_stop < app.end:
        shown.append((last_stop, app.end))
    clock = cv.group(night, cv.uid("g"))
    cv.gate(clock, [span for span in shown if span[1] > span[0]])
    collage_everyday.alarm_clock(cv, clock, **CLOCK, text=HOUR)
    if app.start == 0.0:
        collage_sets.sign(cv, _gated(cv, shot.front, 0.0, app.end), "FROM: MOM", **FROM_CARD, size=64, tilt=-2)
    for i, (at, stop) in enumerate(headlines):
        if app.start <= at < app.end:
            _insert(shot, at, stop, HEADLINES[i], i == len(HEADLINES) - 1)


def _sofa(shot) -> None:
    """Her night: the room dimmed above and below the shelf, which stays in the lamp's pool and under no wash, the
    lamp's warmth on her, her phone, the sofa's front."""
    cv = shot.cv
    above = cv.grad("collage-thought-above", [(0, EVENING + "dd"), (1, EVENING + "00")], (0, 0, 0, 1))
    cv.rect(shot.back, 0, 0, cv.width, SHELF_TOP, above)
    wash = cv.grad(
        "collage-thought-wash", [(0, EVENING + "00"), (0.12, EVENING + "aa"), (1, EVENING + "cc")], (0, 0, 0, 1)
    )
    cv.rect(shot.back, 0, 770, cv.width, 1150, wash)
    warm = cv.rgrad("collage-thought-warm", [(0, LAMP + "44"), (1, LAMP + "00")])
    cv.rect(shot.back, 40, 780, 1000, 960, warm)
    collage_everyday.phone(cv, shot.front, **HELD, screen="#23202b")
    collage_photo.sofa(cv, shot.front)


def dress(shot) -> None:
    (_bed if shot.app.who == "gary" else _sofa)(shot)


def sounds(beats: Sequence[Beat], end: float) -> Sequence[Sound]:
    """Her cup: heard, since her figure has no pose that holds one."""
    return (
        Sound("sip", foley.SIP, (_at(beats, "sip"),), -9.0),
        Sound("saucer", foley.CLINK, (_at(beats, "saucer") + HOLD_FOR_THE_WORD,), -12.0),
    )


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": BED, "rosa": HOME},
    dress=dress,
    cast=casting,
    bleed=True,
    sounds=sounds,
    bitrate=BITRATE,
    keyframes=KEYFRAMES,
    bframes=0,
    loudness="-14",
    sentence_rows=True,
    caption_tops={LINES[8].text: ZOOMED_CAPTION_TOP},
)
