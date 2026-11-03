"""Nine Alarms — the sketch as data: one person in every bed sets nine alarms, sleeps through all of them and wakes up
rested, and the other one hears every single one.

Mae lies awake beside Bruno's phone. It goes off at six, and every ten minutes after, on a Saturday. She climbs over
him to hit it, buries it, shuts it in a drawer and sits on the floor against the drawer. It talks to her. Morning:
Bruno stretches, beaming, and is sorry to report that his alarm didn't go off.

Three voices (ElevenLabs premade Sarah as Mae, Bill as Bruno, Alice as the phone). One bed, two people in the shot
(:mod:`srstudio.toon_bed`, :func:`srstudio.toon_pair.figure`). ``ROWS`` act them per beat; :func:`dress` draws the
three settings, :func:`lens` the camera, :func:`count` the overlay that keeps the count and :func:`sounds` the room.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import (
    anatomy_ledger,
    foley,
    scripting,
    signature,
    sketch,
    toon,
    toon_bed,
    toon_everyday,
    toon_house,
    toon_pair,
)
from srstudio.anatomy import Side
from srstudio.scripting import at, times
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon import fh, fx, fy
from srstudio.toon_everyday import Screen
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound, fit_captions
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3402
SLUG = "nine-alarms"
TITLE = "Nine Alarms — Mae, Bruno and the Phone (Toon)"
DESCRIPTION = (
    "A Toon sketch in a dark bedroom: his phone goes off every ten minutes on a Saturday, he sleeps through all of it, "
    "and she hears every one."
)
ACCESSIBILITY = (
    "A cartoon rabbit's eyes snap open in a dark bedroom beside a cartoon bear asleep on his back, mouth open. His "
    "phone lights up on the nightstand and says it is six o'clock. She shakes him and nothing happens. She climbs "
    "over him and hits it, settles, and his arm flops across her face. It goes off again. She reads it: Saturday. She "
    "buries it under her pillow, then shuts it in the bedside drawer and sits on the floor against the drawer as it "
    "buzzes behind her. The drawer slides out by itself and the phone asks, gently, if he ever hears it. No, she "
    "says. In full sun she sits up red-eyed with the phone in her lap. He stretches, beaming, the best sleep of his "
    "life, and tells her his alarm didn't go off. Lines appear in tinted pills and a bar keeps the count of the alarms."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae), Bill (Bruno) and Alice (the phone)."
NOTE = "ElevenLabs premade voices Sarah, Bill and Alice at their natural pace; no reference-voice cloning."
MAE = Speaker(
    "mae", Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"), VoiceSettings(0.6, 0.75, 0.2), "rabbit"
)
BRUNO = Speaker(
    "bruno", Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"), VoiceSettings(0.5, 0.75, 0.3), "bear"
)
PHONE = Speaker("phone", Voice(role="phone", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"), VoiceSettings(0.65, 0.75, 0.15))
TINTS = {"mae": "#f9dbe6", "bruno": "#eccfae", "phone": "#d4e4fb"}
NIGHT, CORNER, MORNING = "hamster", "goat", "sloth"  # never seen: the names of the shots the dress draws whole
BARE = (NIGHT, CORNER, MORNING)
OF = 9  # alarms in all: the reel sees six of them
RABBIT_COAT, BEAR_COAT = "#efe8ee", "#a8764f"
DARK = ("#0d1430", 0.5)
SCALE = 0.72
MAE_AT, BRUNO_AT = (118.0, 876.0), (336.0, 876.0)  # low enough that the quilt covers both of their paws
FLOOR_AT, FLOOR_SCALE = (160.0, 1010.0), 1.16
BAGS = "#a23b5b"
DIM_PAW = "#afa9b0"  # her coat under the night's shade: the lit phone is above the shade, the hand must not glow
LEDGE = (292.0, 522.0, 92.0, 14.0)  # x, y, w, h: over his head, in frame in every cut in and clear of the captions
BAND = toon.CAPTION_TOP + 12.0  # the pills clear the bug

LINES = (
    Line("phone", "Six o'clock. Wake up.", phone=True),
    Line("mae", "Bruno."),
    Line("phone", "It's six ten. Seriously.", phone=True),
    Line("mae", "It's Saturday."),
    Line("phone", "Six twenty. This one's real.", phone=True),
    Line("phone", "Six thirty. Final warning.", gain=-5.0, phone=True),
    Line("phone", "Six forty. I know you're up.", gain=-5.0, phone=True),
    Line("mae", "I'm the only one who's up!"),
    Line("phone", "Six fifty. Does he ever hear me?", gain=-4.0, phone=True),
    Line("mae", "No."),
    Line("bruno", "Best sleep of my life."),
    Line("bruno", "Babe. My alarm didn't go off."),
)
script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
TOP = ("up", "flat", "desk")
OUT = Act("closed", "open", "desk")  # Bruno, on his back: nothing reaches him
ASLEEP = Act("closed", "flat", "desk")
AWAKE = Act("wide", "flat", "desk")
AT_HIM = Act("side", "flat", "desk")
FURIOUS = Act("narrow", "grimace", "desk")
SHUT = Act("closed", "flat", "desk")
DOWN = Act("down", "flat", "desk")
GRIM = Act("narrow", "flat", "desk")
SPENT = Act("half", "flat", "desk")
BEAMING = Act("closed", "grin", "desk")
AT_HER = Act("left", "flat", "desk")

ROWS = (
    (hold(0.0, NIGHT, "", *TOP), ASLEEP, OUT),
    (hold(0.2, NIGHT, "", *TOP), AWAKE, OUT),  # her eyes snap open
    (say(0.4, NIGHT, 0, *TOP, "alarm:1"), AWAKE, OUT),
    (say(2.2, NIGHT, 1, *TOP, "shake"), AT_HIM, OUT),
    (hold(3.0, NIGHT, "", *TOP, "climb"), FURIOUS, OUT),
    (hold(3.8, NIGHT, "", *TOP, "hit"), FURIOUS, OUT),
    (hold(4.2, NIGHT, "", *TOP, "back"), AWAKE, OUT),
    (hold(4.9, NIGHT, "", *TOP, "flop"), AWAKE, OUT),  # his arm comes down across her face
    (hold(5.5, NIGHT, "", *TOP), SHUT, OUT),  # she gives up and shuts her eyes
    (say(6.4, NIGHT, 2, *TOP, "alarm:2"), AWAKE, OUT),
    (hold(7.9, NIGHT, "", *TOP, "grab"), DOWN, OUT),  # the medium: the phone in her hand
    (say(8.4, NIGHT, 3, *TOP), DOWN, OUT),
    (say(9.8, NIGHT, 4, *TOP, "alarm:3"), GRIM, OUT),
    (hold(11.3, NIGHT, "", *TOP, "bury"), FURIOUS, OUT),  # under the pillow, and she lies on it
    (hold(11.6, NIGHT, "", *TOP), SHUT, OUT),
    (say(11.9, NIGHT, 5, *TOP, "alarm:4"), SHUT, OUT),
    (hold(13.7, CORNER, "", *TOP, "shut"), FURIOUS, OUT),  # the drawer slammed; she sits against it
    (say(14.2, CORNER, 6, *TOP, "alarm:5"), GRIM, OUT),
    (say(16.0, CORNER, 7, *TOP), FURIOUS, OUT),
    (hold(17.7, CORNER, "", *TOP, "sag"), SPENT, OUT),  # the held silence
    (hold(18.5, CORNER, "", *TOP, "slide"), SPENT, OUT),  # the drawer, by itself
    (say(18.9, CORNER, 8, *TOP, "alarm:6"), SPENT, OUT),
    (say(21.2, CORNER, 9, *TOP), SPENT, OUT),
    (hold(22.2, MORNING, "", *TOP, "day"), SPENT, BEAMING),  # full sun; the stretch starts
    (say(22.5, MORNING, 10, *TOP), SPENT, BEAMING),
    (hold(24.2, MORNING, "", *TOP, "turn"), SPENT, AT_HER),  # the held silence: he turns to her
    (first(25.5, MORNING, 11, "Babe.", *TOP), SPENT, AT_HER),
    (part(26.3, MORNING, 11, 1, "My alarm didn't go off.", *TOP, "face"), SPENT, AT_HER),  # Mae's face to the last word
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
ONCE = ("shake", "climb", "hit", "back", "flop", "grab", "bury", "shut", "sag", "slide", "day", "turn", "face")
END = 27.75
SKETCH = Sketch(SLUG, TITLE, (MAE, BRUNO, PHONE), LINES, BEATS, END, tail=0.3, bare=BARE)
TONE = foley.Burst(0.13, 400.0, attack=0.002, decay=0.5, tone_hz=2200.0, tone_end_hz=2200.0, tone=1.0)
TONE_LOW = foley.Burst(0.16, 300.0, attack=0.004, decay=0.5, tone_hz=720.0, tone_end_hz=720.0, tone=0.8)
BUZZ = foley.Burst(0.34, 300.0, attack=0.004, decay=0.8, tone_hz=150.0, tone_end_hz=150.0, tone=0.8, flutter_hz=52.0)
STRETCH = foley.Burst(0.9, 520.0, attack=0.1, decay=0.8, tone_hz=210.0, tone_end_hz=120.0, tone=0.55, flutter_hz=17.0)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, the six alarms come in order and the events in the script's order."""
    sketch.check(sk)
    scripting.speaks_by(sk.beats, 0.5)
    scripting.only_events(sk.beats, {*ONCE, "alarm"})
    for kind in ONCE:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    if [n for _, n in sketch.events(sk.beats, "alarm")] != ["1", "2", "3", "4", "5", "6"]:
        raise sketch.SketchError("the alarms run from one to six")
    order = [at(sk.beats, kind) for kind in ONCE]
    if order != sorted(order):
        raise sketch.SketchError("the events run in the script's order")


def alarm(beats, n: int) -> float:
    return times(beats, "alarm")[n - 1]


def buried(beats) -> float:
    """When the phone in her hand is gone under the pillow."""
    return at(beats, "bury") + 0.25


def count(cv, parent, beats, end, measure) -> None:
    """The overlay: which alarm this is, from just before its line to just after it starts, never its words, and never
    while the phone in her hand still reads the alarm before."""
    alarms, gone = times(beats, "alarm"), buried(beats)
    for n, start in enumerate(alarms, 1):
        lead = max(start - 0.3, gone if start > gone else 0.0)
        toon_house.key_line(cv, parent, f"ALARM {n} OF {OF}", lead, start + 1.5, measure=measure)


def sounds(beats, end) -> tuple[Sound, ...]:
    """Her alarm, loud in the room and low through a pillow and a drawer; his snore, only ever in the bed; the rest."""
    alarms = times(beats, "alarm")
    pips = lambda t: tuple(p for p in (round(t - 0.32, 3), round(t - 0.16, 3), round(t, 3)) if p >= 0.0)  # noqa: E731
    loud = tuple(p for t in alarms[:3] for p in pips(t))
    low = tuple(p for t in alarms[3:5] for p in pips(t))
    climb, flop, grab, bury = (at(beats, k) for k in ("climb", "flop", "grab", "bury"))
    hit, shake = at(beats, "hit"), at(beats, "shake")
    return (
        Sound("alarm", TONE, loud, -15.0),
        Sound("alarm-low", TONE_LOW, low, -17.0),
        Sound("alarm-last", TONE, (round(alarms[5] - 0.2, 3),), -27.0),
        Sound("snore", foley.SNORE, (0.9, round(shake + 0.55, 3), round(flop + 0.1, 3), round(grab - 0.2, 3)), -14.0),
        Sound("thud", foley.THUD, (hit, flop), -9.0),
        Sound("climb", foley.SWISH, (climb,), -22.0),
        Sound("slam", foley.SLAM, (at(beats, "shut"),), -9.0),
        Sound("bury", foley.SWISH, (bury,), -20.0),
        Sound("buzz", BUZZ, (alarms[3], round(alarms[3] + 0.8, 3), alarms[4], round(alarms[4] + 0.8, 3)), -14.0),
        Sound("slide", foley.SCRAPE, (at(beats, "slide"),), -15.0),
        Sound("bird", foley.BIRD, tuple(round(at(beats, "day") + k, 3) for k in (0.15, 0.5, 2.6, 3.0)), -22.0),
        Sound("stretch", STRETCH, (at(beats, "day"),), -14.0),
    )


def _lit_phone(cv, parent, spot, spans) -> None:
    """A phone standing at ``spot``, its screen lit in ``spans``, over the dark, so it is the room's only light."""
    x, y = spot
    w, h = 36.0, 70.0
    for a, b in spans:
        g = cv.group(parent, cv.uid("g"), start=a, end=b)
        halo = cv.rgrad("nine-alarms-halo", [(0.0, "#bcd6ffaa"), (1.0, "#bcd6ff00")])
        cv.ellipse(g, fx(x - 150), fy(y - h / 2 - 150), fh(300), fh(300), halo)
        cv.rect(g, fx(x - w / 2 + 3), fy(y - h + 3), fh(w - 6), fh(h - 6), "#dcebff", radius=fh(3))


def _mae_track(cv, g, beats) -> None:
    """She leans in to shake him, crosses him, reaches the phone, comes back, and sinks onto the pillow."""
    x, y = fx(MAE_AT[0]), fy(MAE_AT[1])
    shake, climb, hit, back, bury = (at(beats, k) for k in ("shake", "climb", "hit", "back", "bury"))
    over, far = fx(226.0), fx(318.0)
    xs = [(0.0, x), (shake, x), (shake + 0.2, x + 26), (shake + 0.4, x), (climb, x), (climb + 0.4, over), (hit, far),
          (back, far), (back + 0.55, x)]  # fmt: skip
    ys = [(0.0, y), (climb, y), (climb + 0.4, y - 44), (hit, y - 26), (back, y - 26), (back + 0.3, y - 36),
          (back + 0.55, y), (bury, y), (bury + 0.3, y + 36)]  # fmt: skip
    turn = [(0.0, 0.0), (climb, 0.0), (climb + 0.4, 6.0), (hit, 8.0), (back, 8.0), (back + 0.55, 0.0)]
    cv.keys(g, "x", xs, hold=False, kind="sine-in-out", local=False)
    cv.keys(g, "y", ys, hold=False, kind="sine-in-out", local=False)
    cv.keys(g, "rotation", turn, hold=False, kind="sine-in-out", local=False)


def _bruno_track(cv, g, beats) -> None:
    """Shaken, then squashed as she goes over him; nothing else."""
    x, y = fx(BRUNO_AT[0]), fy(BRUNO_AT[1])
    shake, climb = at(beats, "shake"), at(beats, "climb")
    xs = [(0.0, x), *((shake + k * 0.09, x + (-1) ** k * 16) for k in range(1, 7)), (shake + 0.63, x)]
    cv.keys(g, "x", xs, hold=False, local=False)
    cv.keys(g, "y", [(0.0, y), (climb + 0.2, y), (climb + 0.5, y + 28), (climb + 1.2, y)], hold=False, local=False)


def _ledge(cv, parent) -> None:
    """The ledge on the headboard that signs the bed: the nightstand leaves the frame in both cut ins, this does not."""
    x, y, w, h = LEDGE
    cv.rect(parent, fx(x), fy(y), fh(w), fh(h), toon_house.NIGHTSTAND, cv.ink, toon.FINE_W, radius=fh(3))
    signature.cactus(cv, parent, fx(x + 24), fy(y), 0.7)
    signature.code(cv, parent, fx(x + w - 4), fy(y - 11), 14, color="#b9a48f", opacity=0.9, align="end")


def _night(shot) -> None:
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_bed.double_bed(cv, shot.back)
    _ledge(cv, shot.back)
    bear = toon_pair.figure(shot, shot.back, "bear", BRUNO_AT, ACTS["bear"], scale=SCALE, moving=False)
    _bruno_track(cv, bear, beats)
    rabbit = toon_pair.figure(shot, shot.back, "rabbit", MAE_AT, ACTS["rabbit"], scale=SCALE)
    _mae_track(cv, rabbit, beats)
    flop, grab, hit, bury = at(beats, "flop"), at(beats, "grab"), at(beats, "hit"), at(beats, "bury")
    a1, a2, a3 = alarm(beats, 1), alarm(beats, 2), alarm(beats, 3)
    with anatomy_ledger.on_arm("bear", Side.LEFT):
        toon_bed.swung_arm(cv, shot.back, (268.0, 778.0), BEAR_COAT, [(flop, 250.0), (flop + 0.22, 203.0)], flop,
                           grab, length=150.0)  # fmt: skip
    toon_bed.double_quilt(cv, shot.front, signed=False)
    px, py = toon_bed.PHONE_SPOT
    stood = cv.group(shot.front, cv.uid("g"), start=app.start, end=grab)  # in her hand from here on, never on the stand
    cv.rect(
        stood, fx(px - 18), fy(py - 70), fh(36), fh(70), toon_everyday.PHONE_BODY, cv.ink, toon.FINE_W, radius=fh(5)
    )
    with anatomy_ledger.on_arm("rabbit", Side.RIGHT):
        toon_bed.swung_arm(cv, shot.front, (372.0, 760.0), RABBIT_COAT, [(hit - 0.2, -14.0), (hit, 24.0)], hit - 0.2,
                           hit + 0.3, length=150.0, width=54.0)  # fmt: skip
    held_from, held_to = grab, buried(beats)
    with anatomy_ledger.on_arm("rabbit", Side.RIGHT):
        toon_bed.swung_arm(cv, shot.front, (204.0, 776.0), RABBIT_COAT, [(grab, -12.0)], held_from, held_to,
                           length=72.0, width=44.0)  # fmt: skip
    shade = cv.group(shot.front, cv.uid("g"))
    cv.rect(shade, 0, 0, cv.width, cv.height, DARK[0], opacity=DARK[1])
    _lit_phone(cv, shot.front, toon_bed.PHONE_SPOT, ((max(0.05, a1 - 0.3), hit), (a2 - 0.3, grab)))
    held = cv.group(shot.front, cv.uid("g"), start=held_from, end=held_to)
    buzz = [(a3 + k * 0.05, (-1) ** k * 7.0) for k in range(7)]
    cv.keys(held, "x", [(grab, 0.0), (a3 - 0.05, 0.0), *buzz, (a3 + 0.4, 0.0)], hold=False, local=False)
    toon_everyday.phone(
        cv, held, tuple(Screen(t, "notify", title="Alarm", text="Saturday", note=n)
                        for t, n in ((0.0, "6:10"), (a3, "6:20"))), measure=shot.measure,
        at=(306.0, 830.0), scale=0.9, hand=DIM_PAW, id="in-her-hand",
    )  # fmt: skip
    pillow = cv.group(shot.front, cv.uid("g"), start=bury + 0.3, end=app.end)
    halo = cv.rgrad("nine-alarms-halo", [(0.0, "#bcd6ffaa"), (1.0, "#bcd6ff00")])
    glow = cv.ellipse(pillow, fx(-30.0), fy(620.0), fh(170.0), fh(170.0), halo)
    pulse = [(bury + 0.3 + k * 0.4, 0.5 if k % 2 else 1.0) for k in range(int((app.end - bury) / 0.4) + 1)]
    cv.keys(glow, "opacity", pulse, hold=False, local=False)


def _corner(shot) -> None:
    cv, app, beats = shot.cv, shot.app, shot.beats
    a5 = alarm(beats, 5)
    toon_bed.floor_corner(cv, shot.back)
    buzz = (a5, a5 + 0.8)
    toon_bed.bedside_drawer(cv, shot.back, buzzes=buzz, slides=at(beats, "slide"), lit=0.85)
    g = toon_pair.figure(shot, shot.back, "rabbit", FLOOR_AT, ACTS["rabbit"], scale=FLOOR_SCALE)
    y, sag = fy(FLOOR_AT[1]), at(beats, "sag")
    jolts = [(t + k, y + d) for t in buzz for k, d in ((0.0, 0.0), (0.06, -9.0), (0.14, 7.0), (0.22, -5.0), (0.3, 0.0))]
    cv.keys(g, "y", [(app.start, y), *jolts, (sag, y), (sag + 0.5, y + 26)], hold=False, local=False)
    toon_bed.quilt_heap(cv, shot.front)
    shade = cv.group(shot.front, cv.uid("g"))
    cv.rect(shade, 0, 0, cv.width, cv.height, DARK[0], opacity=DARK[1])


def _bags(cv, parent) -> None:
    """Two raw red rims under her eyes, on the figure's own coordinates."""
    for x, y in ((123.0, 591.0), (194.0, 582.0)):
        cv.path(parent, f"M {fx(x)} {fy(y)} q {fh(19)} {fh(13)} {fh(38)} 0", None, BAGS, 8.0)
        cv.path(parent, f"M {fx(x + 5)} {fy(y + 11)} q {fh(14)} {fh(9)} {fh(28)} 0", None, BAGS, 5.0)


def _morning(shot) -> None:
    cv, beats = shot.cv, shot.beats
    toon_bed.double_bed(cv, shot.back, day=True)
    _ledge(cv, shot.back)
    day, turn = at(beats, "day"), at(beats, "turn")
    for shoulder, up, side in (((322.0, 768.0), -118.0, Side.LEFT), ((378.0, 768.0), -62.0, Side.RIGHT)):
        keys = [(day, 90.0), (day + 0.8, up), (turn - 0.45, up), (turn, 90.0)]
        with anatomy_ledger.on_arm("bear", side):
            toon_bed.swung_arm(cv, shot.back, shoulder, BEAR_COAT, keys, day, turn + 0.05, length=290.0)
    bear = toon_pair.figure(shot, shot.back, "bear", BRUNO_AT, ACTS["bear"], scale=SCALE)
    cv.keys(bear, "rotation", [(turn, 0.0), (turn + 0.4, -7.0)], hold=False, kind="sine-in-out", local=False)
    rabbit = toon_pair.figure(shot, shot.back, "rabbit", MAE_AT, ACTS["rabbit"], scale=SCALE, moving=False)
    _bags(cv, rabbit)
    toon_bed.double_quilt(cv, shot.front, day=True, signed=False)
    lap = "M {} {} L {} {} L {} {} L {} {} Z"
    corners = (fx(96.0), fy(846.0), fx(214.0), fy(838.0), fx(236.0), fy(884.0), fx(104.0), fy(894.0))
    cv.path(shot.front, lap.format(*corners), toon_everyday.PHONE_BODY, cv.ink, toon.FINE_W)


def dress(shot) -> None:
    """The bed by night, the floor by the drawer, the bed by day."""
    {NIGHT: _night, CORNER: _corner, MORNING: _morning}[shot.app.who](shot)


def captions(cv, parent, lines, measure, tints) -> None:
    """The style's pills, in the lower band that clears the bug."""
    pills = partial(measure, size=toon.CAPTION_SIZE)
    fit_captions(lines, pills, cv.width)
    toon.captions(cv, parent, lines, pills, tints=tints, band=BAND)


def lens(shot, setup) -> None:
    """A slow push across the opening, a cut in on Mae for the phone, back out; a slow push on her on the floor; a cut
    in on the bed for the last line, her face and his both whole. Each cut in keeps :data:`LEDGE` in frame. The
    captions stay where they are."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.who == NIGHT:
        grab, a3 = at(beats, "grab"), alarm(beats, 3)
        rise = lambda t: 1.0 + 0.03 * t / grab  # noqa: E731
        scale = [(0.0, 1.0), (grab - 0.02, rise(grab)), (grab, 1.55), (a3 - 0.02, 1.55), (a3, 1.03), (app.end, 1.03)]
        cv.keys(setup, "scaleX", scale, hold=False, local=False)
        cv.keys(setup, "scaleY", scale, hold=False, local=False)
        x0, y0 = 540.0, 1000.0
        place = lambda s, c: round(c * (1 - s), 2)  # noqa: E731
        xs = [(t, place(s, x0)) if s < 1.2 else (t, -24.0) for t, s in scale]
        ys = [(t, place(s, y0)) if s < 1.2 else (t, -650.0) for t, s in scale]
        cv.keys(setup, "x", xs, hold=False, local=False)
        cv.keys(setup, "y", ys, hold=False, local=False)
    elif app.who == CORNER:
        sag = at(beats, "sag")
        scale = [(app.start, 1.0), (sag, 1.0), (app.end, 1.07)]
        cv.keys(setup, "scaleX", scale, hold=False, kind="sine-in-out", local=False)
        cv.keys(setup, "scaleY", scale, hold=False, kind="sine-in-out", local=False)
        ys = [(t, round(900.0 * (1 - s), 2)) for t, s in scale]
        xs = [(t, round(360.0 * (1 - s), 2)) for t, s in scale]
        cv.keys(setup, "x", xs, hold=False, kind="sine-in-out", local=False)
        cv.keys(setup, "y", ys, hold=False, kind="sine-in-out", local=False)
    else:
        face = at(beats, "face")
        s = 1.35
        cv.keys(setup, "scaleX", [(app.start, 1.0), (face, s)], local=False)
        cv.keys(setup, "scaleY", [(app.start, 1.0), (face, s)], local=False)
        cv.keys(setup, "x", [(app.start, 0.0), (face, -85.0)], local=False)
        cv.keys(setup, "y", [(app.start, 0.0), (face, -500.0)], local=False)
