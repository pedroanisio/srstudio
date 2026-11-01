"""Absolutely Right — the sketch as data: the chatbot tells each of us we are right, so now both sides of a fight have a
brilliant, supportive advisor. Mia and Brock type back to back on the sofa and read their phones out loud at each other,
until her advice turns out to be his, candle shop and all, and both phones agree with them both.

Two voices (ElevenLabs premade River as Mia, Roger as Brock), held on a medium two-shot on the sofa in the lounge
(:func:`srstudio.toon_pair.figure`), both phones with their backs to the viewer. Mia turns round in the held silence and
the shot cuts in on her phone, the first screen the viewer reads; the last shot is the two-shot again, both windows
facing out, and the same chip lands on each. The first shot pushes in from its first frame. ``ROWS`` act both characters
per beat; :func:`validate` checks the events; :func:`dress` draws each shot and :func:`lens` its camera.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from srstudio import camera, scripting, sketch, toon_chat, toon_house, toon_pair, toon_rooms, toon_sketch
from srstudio import foley as keys
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_chat import Bubble
from srstudio.toon_pair import Act
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3319
SLUG = "absolutely-right"
TITLE = "Absolutely Right — Mia, Brock and the Advisors (Toon)"
DESCRIPTION = (
    "A Toon sketch on a sofa: a couple three days into a fight type to their chatbots back to back, until both "
    "advisors turn out to say exactly the same thing."
)
ACCESSIBILITY = (
    "A cartoon rabbit and a cartoon bear sit on a sofa at night, turned away from each other, each reading a phone "
    "out loud. Each phone calls its owner absolutely right. The advice escalates until the bear reads out that he "
    "should leave her and open a candle shop. After a silence the rabbit turns round and holds up her phone: the same "
    "words. Both phones buzz, and the same chip lands on each: You're absolutely right. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices River (Mia) and Roger (Brock)."
NOTE = "ElevenLabs premade voices River and Roger at their natural pace; no reference-voice cloning."
PLAIN = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3)
MIA = Speaker("mia", Voice(role="mia", id="SAz9YHcvj6GT2YYXdXww", name="River"), PLAIN, "rabbit")
BROCK = Speaker("brock", Voice(role="brock", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"), PLAIN, "bear")
TINTS = {"mia": "#ffd9e4", "brock": "#d9e8ff"}
PAIR = "hamster"  # never seen: the name of the two-shot, a shot the dress draws whole
BARE = (PAIR,)
LIT = True
HEADS = ("rabbit",)
FIGURES = {"rabbit": (1.16, 8.0)}
LIGHTS = {"tv": ((0.0, "off", "blue"),), "lamp": ((0.0, "on"),)}
SEATS = {"rabbit": (146.0, 840.0), "bear": (424.0, 840.0)}
AWAY = {"rabbit": -7.0, "bear": 7.0}  # degrees: turned away from each other
TURNED = 3.0  # degrees, Mia towards him
TURN_TIME = 0.35
PHONES = {"rabbit": (150.0, 884.0), "bear": (420.0, 884.0)}
PHONE_SCALE = 0.92
FACING = {"rabbit": (150.0, 938.0), "bear": (420.0, 938.0)}
FACING_SCALE = 1.2
BIG_PHONE = dict(at=(372.0, 990.0), scale=1.75)
CHIPS = {"rabbit": (150.0, 850.0), "bear": (420.0, 850.0)}
CHIP = "You're absolutely right"
CHIP_SIZE = 32
ADVICE = "Leave him and open a candle shop."
HOOK = "DAY 3 OF THE FIGHT"
PIVOT = (980.0, 1420.0)
END = 26.6
TYPING_LINES = 5  # they stop typing when the anniversary comes up
KEYS_GAIN_DB = -6.0

LINES = (
    Line("mia", "\"You're absolutely right, and that must be so hard.\""),
    Line("brock", "\"What a brilliant point. You're absolutely right.\""),
    Line("mia", "Mine says you're defensive."),
    Line("brock", "Mine says yours is projecting."),
    Line("mia", "Ask it who forgot the anniversary."),
    Line("brock", "\"Great question! Anniversaries are a construct.\""),
    Line("mia", "Mine says I should leave you."),
    Line("brock", "Mine too."),
    Line("mia", "To leave me?"),
    Line("brock", "To leave you and open a candle shop."),
    Line("mia", "That was my candle shop."),
)

script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
READ = Act("down", "flat", "desk")
SMUG = Act("down", "smirk", "desk")
HURT = Act("narrow", "flat", "desk")
STILL = Act("half", "flat", "desk")
BLANK = Act("wide", "flat", "desk")
AT_HIM = Act("side", "flat", "desk")
BACK_ON = Act("down", "grimace", "desk", ("sweat",))
TOP = ("half", "flat", "desk")
TYPING = ("half", "flat", "type")  # the beat's arms drive the foley: the two-shot draws its own figures

ROWS = (
    (hold(0.0, PAIR, "", *TYPING), READ, READ),
    (first(0.3, PAIR, 0, "\"You're absolutely right,", *TYPING), READ, READ),
    (part(1.7, PAIR, 0, 3, "and that must be so hard.\"", *TYPING), SMUG, READ),
    (first(3.1, PAIR, 1, "\"What a brilliant point.", *TYPING), SMUG, READ),
    (part(4.3, PAIR, 1, 4, "You're absolutely right.\"", *TYPING), READ, SMUG),
    (say(5.8, PAIR, 2, *TYPING), SMUG, READ),
    (say(7.3, PAIR, 3, *TYPING), HURT, SMUG),
    (say(9.35, PAIR, 4, *TYPING), HURT, READ),
    (first(11.2, PAIR, 5, "\"Great question!", *TOP), HURT, BACK_ON),
    (part(12.2, PAIR, 5, 2, "Anniversaries are a construct.\"", *TOP), HURT, SMUG),
    (say(14.1, PAIR, 6, *TOP, "closer"), SMUG, READ),
    (say(15.7, PAIR, 7, *TOP), BLANK, SMUG),
    (say(16.7, PAIR, 8, *TOP), HURT, SMUG),
    (first(17.85, PAIR, 9, "To leave you", *TOP), BLANK, READ),
    (part(18.75, PAIR, 9, 3, "and open a candle shop.", *TOP), BLANK, SMUG),
    (hold(20.2, PAIR, "", *TOP), BLANK, READ),  # two seconds: nothing, then she turns
    (hold(21.0, PAIR, "", *TOP, "turn"), AT_HIM, READ),
    (hold(21.75, "rabbit", "", "side", "flat", "desk"), AT_HIM, READ),  # her phone, the first screen we read
    (say(22.6, "rabbit", 10, "narrow", "flat", "desk"), AT_HIM, READ),
    (hold(24.2, PAIR, "", *TOP, "toast"), Act("down", "flat", "desk"), Act("wide", "flat", "desk", ("sweat",))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
SKETCH = Sketch(SLUG, TITLE, (MIA, BROCK), LINES, BEATS, END, bare=(PAIR,))


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, Mia turns once and the phones buzz once after every line, and nothing
    else happens: no window faces out before she turns."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    for kind in ("turn", "toast", "closer"):
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    scripting.only_events(sk.beats, {"turn", "toast", "closer"})
    if sketch.events(sk.beats, "toast")[0][0] <= max(b.start for b in sk.beats if b.spoken):
        raise sketch.SketchError("the phones buzz after the last line")


def foley(
    beats: Sequence[sketch.Beat], end: float, speech: Sequence[tuple[float, float]], root: Path, seed: int
) -> list[dict]:
    """The buzz, and a short run of keys before the first line and in each breath while they still type: the house
    keys need a longer gap than these lines leave."""
    out = toon_sketch.sound_effects(beats, end, speech, root, seed)
    breaths = [0.02, *(stop + 0.03 for _, stop in speech[:TYPING_LINES])]
    taps = [t for t in keys.taps(breaths, seed=seed) if not any(a <= t <= z for a, z in speech)]
    path = keys.write_typing(Path(root) / "audio" / "keys.wav", taps, end, seed=seed, peak=toon_sketch.TYPING_PEAK)
    return [*out, sketch.effect("keys", 0.0, KEYS_GAIN_DB, root, path, taps)]


def _pair(shot, turn: float, buzz: float) -> None:
    cv, app = shot.cv, shot.app
    for who in ("rabbit", "bear"):
        g = toon_pair.figure(shot, shot.back, who, SEATS[who], ACTS[who])
        away = AWAY[who]
        if app.start >= turn:
            g.rotation = TURNED if who == "rabbit" else 0.0
        elif who == "rabbit" and app.start < turn < app.end:
            g.rotation = away
            cv.keys(g, "rotation", [(turn, away), (turn + TURN_TIME, TURNED)], kind="sine-in-out", local=False)
        else:
            g.rotation = away
    toon_house.ledge(cv, shot.front, "oak")
    for who in ("rabbit", "bear"):
        words = ADVICE if who == "rabbit" else "Leave her and open a candle shop."
        last = app.start >= turn
        toon_chat.chat_phone(cv, shot.front, (Bubble(0.0, words),), measure=shot.measure,
                             at=(FACING if last else PHONES)[who], scale=FACING_SCALE if last else PHONE_SCALE,
                             face_from=buzz if last else app.end, buzz=(buzz,), id=cv.uid("phone"))  # fmt: skip
        if app.start >= turn:
            toon_chat.chat_chip(cv, shot.front, CHIP, buzz, app.end, measure=shot.measure, at=CHIPS[who],
                                size=CHIP_SIZE, id=cv.uid("chip"))  # fmt: skip


def dress(shot) -> None:
    """The lounge, lamp on; the two-shot with both phones' backs to the viewer until the last shot, Mia's phone huge in
    her close-up, and the hook over the first shot."""
    cv, app = shot.cv, shot.app
    toon_rooms.dress(shot, "lounge", LIGHTS)
    turn = sketch.events(shot.beats, "turn")[0][0]
    buzz = sketch.events(shot.beats, "toast")[0][0]
    if app.who == PAIR:
        _pair(shot, turn, buzz)
    else:
        toon_house.ledge(cv, shot.front, "oak")
        toon_chat.chat_phone(cv, shot.front, (Bubble(0.0, ADVICE),), measure=shot.measure, id=cv.uid("phone"),
                             **BIG_PHONE)  # fmt: skip
    if app.start == 0.0:
        toon_house.key_line(cv, shot.front, HOOK, 0.0, 2.6, measure=shot.measure)


def lens(shot, setup) -> None:
    """A slow push from the first frame; a step closer when the advice turns on them."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start == 0.0:
        closer = sketch.events(shot.beats, "closer")[0][0]
        scale = [(0.0, 1.0), (3.0, 1.04), (closer, 1.04), (closer + 0.01, 1.09)]
        if shot.app.end > closer:
            camera.push_in(shot.cv, setup, scale=scale)
