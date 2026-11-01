"""One Bar — the sketch as data: everyone has one spot in the house where the signal lives, and it is never a good one.

Gil stands on a chair on a table with one arm up and one bar on the phone. Mia keeps him fed and tells him not to move.
The upload he is nursing turns out to be a complaint about the signal.

Two voices (ElevenLabs premade Chris as Gil, River as Mia) on one held wide in a hall
(:func:`srstudio.toon_pair.figure`). ``ROWS`` act both per beat; :func:`dress` draws the shot and :func:`lens`
its camera; :func:`validate` checks the events. The arm and the phone never move: everything else in the shot does.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, foley, readings, scripting, sketch, toon_chat, toon_house, toon_pair, toon_signal
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3318
SLUG = "one-bar"
TITLE = "One Bar — Gil, Mia and the Upload (Toon)"
DESCRIPTION = (
    "A Toon sketch in a hallway: a man stands on a chair on a table, one arm in the air, nursing an upload on one bar "
    "of signal while his partner feeds him a sandwich on a broom."
)
ACCESSIBILITY = (
    "A cartoon frog stands on a chair on a table in a hallway, one arm straight up, holding a phone near the ceiling. "
    "A chip reads nine percent. A cartoon rabbit behind the table lifts a sandwich to him on a broom and he bites it "
    "without lowering the arm. The chair tips on two legs and the arm does not move. The upload is a complaint about "
    "the signal. It reaches sent and a reply arrives: please log in to our website. The last bar goes out. The arm "
    "stays up. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Chris (Gil) and River (Mia)."
NOTE = "ElevenLabs premade voices Chris and River at their natural pace; no reference-voice cloning."
PLAIN = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3)
DEADPAN = VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15)
GIL = Speaker("gil", Voice(role="gil", id="iP95p4xoKVk53GoZ742B", name="Chris"), DEADPAN, "frog")
MIA = Speaker("mia", Voice(role="mia", id="SAz9YHcvj6GT2YYXdXww", name="River"), PLAIN, "rabbit")
TINTS = {"gil": "#ddf5d0", "mia": "#ffd9e4"}
PAIR = "hamster"  # never seen: the name of the shot the dress draws whole
BARE = (PAIR,)
SEATS = {"frog": (168.0, 650.0), "rabbit": (374.0, 962.0)}
SCALES = {"frog": 0.72, "rabbit": 0.95}
CHAIR_AT = (200.0, 806.0)
FOOT = (80.0, 806.0)  # the leg the chair tips on
TIP = -6.5  # degrees
ARM_HAND = (122.0, 270.0)
FROG, FROG_DARK = "#7fcf6b", "#4f9a46"
CHIP_AT = (432.0, 392.0)
BROOM_LOW, BROOM_UP = (233.0, 900.0), (262.0, 480.0)
BROOM_TILT = 4.0  # degrees: up past her ear to his mouth
REPLY_PHONE_LOW, REPLY_PHONE_UP = 1110.0, 960.0
HOOK = "9% SENDING"
HOOK_END = 3.0
PIVOT = (980.0, 1420.0)  # the marks stay where they are as the camera comes in
END = 25.4

LINES = (
    Line("gil", "One bar."),
    Line("mia", "Don't move."),
    Line("gil", "It's sending."),
    Line("mia", "How much?"),
    Line("gil", "Nine percent."),
    Line("mia", "Lean left."),
    Line("gil", "That's the neighbor's bar."),
    Line("mia", "What are we even sending?"),
    Line("gil", "The complaint."),
    Line("mia", "What complaint?"),
    Line("gil", "About the signal."),
    Line("mia", "Sorry to hear that! Please log in to our website."),
)

script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
GIL_UP = Act("up", "flat", "desk")
GIL_STILL = Act("wide", "flat", "desk")
GIL_BITE = Act("side", "open", "desk")
GIL_CHEW = Act("up", "puff", "desk")
GIL_CHEW_2 = Act("up", "flat", "desk")
GIL_SWEAT = Act("wide", "flat", "desk", ("sweat",))
GIL_AT_HER = Act("side", "flat", "desk")
GIL_HOPE = Act("wide", "grimace", "desk")
GIL_LOST = Act("half", "flat", "desk")
MIA_UP = Act("up", "flat", "desk")
MIA_FIRM = Act("narrow", "flat", "desk")
MIA_WIDE = Act("wide", "flat", "desk")
MIA_DOWN = Act("down", "flat", "desk")
MIA_LOST = Act("half", "flat", "desk")
TOP = ("up", "flat", "desk")

ROWS = (
    (hold(0.0, PAIR, "", *TOP, "wobble"), GIL_UP, MIA_UP),
    (say(0.3, PAIR, 0, *TOP), GIL_UP, MIA_UP),
    (say(1.3, PAIR, 1, *TOP), GIL_STILL, MIA_FIRM),
    (say(2.3, PAIR, 2, *TOP), GIL_UP, MIA_UP),
    (say(3.4, PAIR, 3, *TOP), GIL_UP, MIA_UP),
    (say(4.3, PAIR, 4, *TOP), GIL_UP, MIA_UP),
    (hold(5.6, PAIR, "", *TOP, "lift"), GIL_UP, MIA_UP),  # she lifts it to him on the broom
    (hold(6.5, PAIR, "", *TOP, "bite"), GIL_BITE, MIA_UP),  # he eats; the arm stays
    (hold(6.9, PAIR, "", *TOP), GIL_CHEW, MIA_UP),
    (hold(7.2, PAIR, "", *TOP), GIL_CHEW_2, MIA_UP),
    (hold(7.5, PAIR, "", *TOP), GIL_CHEW, MIA_UP),
    (hold(7.8, PAIR, "", *TOP, "lower"), GIL_CHEW_2, MIA_UP),
    (say(8.3, PAIR, 5, *TOP), GIL_UP, MIA_FIRM),
    (say(9.3, PAIR, 6, *TOP), GIL_AT_HER, MIA_UP),
    (hold(10.7, PAIR, "", *TOP, "tip"), GIL_SWEAT, MIA_WIDE),  # two legs; he holds; the arm has not moved
    (hold(12.1, PAIR, "", *TOP), GIL_SWEAT, MIA_WIDE),
    (say(13.1, PAIR, 7, *TOP, "settle"), GIL_UP, MIA_UP),
    (say(14.7, PAIR, 8, *TOP), GIL_UP, MIA_UP),
    (say(15.8, PAIR, 9, *TOP), GIL_UP, MIA_FIRM),
    (say(16.8, PAIR, 10, *TOP), GIL_UP, MIA_UP),
    (hold(18.4, PAIR, "", *TOP, "sent"), GIL_HOPE, MIA_WIDE),  # ding: they do not dare cheer
    (hold(20.0, PAIR, "", *TOP, "reply"), GIL_HOPE, MIA_DOWN),  # ding: a reply, on her phone
    (first(20.7, PAIR, 11, "Sorry to hear that!", *TOP), GIL_HOPE, MIA_DOWN),
    (part(21.9, PAIR, 11, 4, "Please log in to our website.", *TOP), GIL_LOST, MIA_DOWN),
    (hold(23.7, PAIR, "", *TOP, "dark"), GIL_LOST, MIA_LOST),  # the last bar goes out; the arm stays up
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"frog": tuple(row[1] for row in ROWS), "rabbit": tuple(row[2] for row in ROWS)}
EVENTS = ("wobble", "lift", "bite", "lower", "tip", "settle", "sent", "reply", "dark")
SKETCH = Sketch(SLUG, TITLE, (GIL, MIA), LINES, BEATS, END, bare=BARE)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, and every event comes once, in the script's order."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    for kind in EVENTS:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [when(sk.beats, kind) for kind in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError("the events run in the script's order")


def when(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def progress(beats, end) -> tuple[tuple[readings.Reading, ...], tuple[float, ...]]:
    """The chip: nine percent while they talk, a crawl over the tip, the rest while they argue, then SENT."""
    lift, settle, sent = when(beats, "lift"), when(beats, "settle"), when(beats, "sent")
    crawl = readings.climbing(9, 13, lift, settle, every=1.5)
    rest = readings.climbing(13, 99, settle, sent - 1.0, every=1.0)
    cues = [(0.0, "9%"), *((at, f"{n}%") for at, n in (*crawl[1:], *rest[1:])), (sent, "SENT")]
    shown = readings.held(cues, end)
    shares = tuple(1.0 if r.text == "SENT" else int(r.text[:-1]) / 100 for r in shown)
    return shown, shares


def sounds(beats, end) -> tuple[Sound, ...]:
    """The chair, the broom, a bite and two dings, and nothing at all at the end."""
    lift, bite, tip, sent, reply = (when(beats, k) for k in ("lift", "bite", "tip", "sent", "reply"))
    chews = tuple(round(bite + 0.32 * k, 3) for k in range(1, 5))
    return (
        Sound("wobble", foley.SCRAPE, (0.08,), -18.0),
        Sound("broom", foley.SWISH, (lift,), -20.0),
        Sound("bite", foley.REMOTE_CLICK, (bite + 0.06,), -14.0),
        Sound("chew", foley.KNOCK, chews, -28.0),
        Sound("tip", foley.SCRAPE, (tip, tip + 0.28), -14.0),
        Sound("ding", foley.BELL, (sent, reply), -10.0),
    )


def _chair(shot, cv) -> object:
    """Gil and the chair in one group, so the chair tips him and leaves the arm where it is."""
    beats = shot.beats
    wobble, tip, settle = when(beats, "wobble"), when(beats, "tip"), when(beats, "settle")
    x, y = toon_house.fx(FOOT[0]), toon_house.fy(FOOT[1])
    g = cv.group(shot.back, "chair-tilt", anchorX=x, anchorY=y, x=x, y=y)
    keys = [
        (wobble, -1.6),
        (0.35, 1.0),
        (0.7, -0.5),
        (1.0, 0.0),
        (tip, 0.0),
        (tip + 0.3, TIP),
        (tip + 0.5, TIP + 1.0),
        (tip + 0.75, TIP),
        (settle - 0.35, TIP),
        (settle, 0.0),
    ]
    cv.keys(g, "rotation", keys, hold=False, kind="sine-in-out", local=False)
    return g


def dress(shot) -> None:
    """The hall, the arm, Gil on his chair, Mia behind the table with the broom, the upload's chip, the table."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_house.hallway(cv, shot.back, door="shut")
    dark = when(beats, "dark")
    toon_signal.raised_phone(cv, shot.back, ARM_HAND, FROG, FROG_DARK, ((0.0, 1), (dark, 0)), 0.0, app.end)
    tilt = _chair(shot, cv)
    toon_pair.figure(shot, tilt, "frog", SEATS["frog"], ACTS["frog"], scale=SCALES["frog"])
    toon_signal.climb_chair(cv, tilt, CHAIR_AT)
    lift, bite, lower = when(beats, "lift"), when(beats, "bite"), when(beats, "lower")
    moves = ((lift, *BROOM_LOW), (lift + 0.7, *BROOM_UP), (lower, *BROOM_UP), (lower + 0.45, *BROOM_LOW))
    toon_signal.broom(cv, shot.back, moves, lift, lower + 0.5, bite + 0.08, tilt=BROOM_TILT)
    toon_pair.figure(shot, shot.back, "rabbit", SEATS["rabbit"], ACTS["rabbit"], scale=SCALES["rabbit"])
    reply = when(beats, "reply")
    never = (toon_chat.Bubble(app.end, "Sorry to hear that!"),)  # her side of the phone: we only ever see its back
    phone = toon_chat.chat_phone(cv, shot.back, never, measure=shot.measure, at=(486.0, REPLY_PHONE_LOW), scale=0.9,
                                 face_from=app.end, id="reply-phone")  # fmt: skip
    y = toon_house.fy(REPLY_PHONE_LOW)
    cv.keys(phone, "y", [(reply, y), (reply + 0.3, toon_house.fy(REPLY_PHONE_UP))], hold=False, local=False)
    shown, shares = progress(beats, app.end)
    toon_signal.upload_chip(cv, shot.back, shown, shares, measure=shot.measure, at=CHIP_AT)
    toon_house.ledge(cv, shot.front, "oak")
    toon_signal.table_legs(cv, shot.front)
    if app.start == 0.0:
        toon_house.key_line(cv, shot.front, HOOK, 0.0, HOOK_END, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push over the tip and over the end; held otherwise, so the arm stays where it was."""
    camera.anchor(setup, *PIVOT, place=True)
    tip, dark = when(shot.beats, "tip"), when(shot.beats, "dark")
    camera.push_in(
        shot.cv, setup, scale=[(0.0, 1.0), (tip, 1.0), (tip + 1.4, 1.015), (dark, 1.015), (dark + 1.5, 1.03)]
    )
