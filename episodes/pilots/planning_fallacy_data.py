"""The Planning Fallacy — a pilot of "There's a Name for That", main trigger recipient: the sketch as data.

A rabbit turns the shower off to send a voice note, says "Five minutes away." in the quiet, and turns it back on. A
bear on a sofa gets it at 7:05 and leaves the phone on the table. "Leaving now.", in a towel, at 7:32. "Almost ready.",
at 7:44. "Do I need a jacket?", at 7:51. She means it. There's a name for that. Then why, and one study, and what to do
before saying a time. And the bear speaks for the first time: the table is at 8:15. "You said seven." "I know."
The reel ends with the water running, on the frame it opens on, so the first second comes round again.

The viewer sends this to the friend who says "five minutes away" from the shower. Text on screen carries every key
point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade Daniel; the two characters are
ElevenLabs premade Alice and Bill. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the
events and every word on screen against :func:`srstudio.mind_kit.check_copy`; :func:`dress` draws each shot and
:func:`foley` its sound.

Every word and figure about the study lives in :data:`STUDY`, :data:`SAID`, :data:`TOOK` and the lines that read them
and traces to ``pilots/mind/planning-fallacy/sources.md``. Days count from the survey call, not from the start of the
thesis; 37 were surveyed and the means are on the 33 who had finished. The turn claims that the optimism went away,
never that anyone got accurate or finished sooner. A voice note, a date for seven and a clock are the characters': no
line says the study measured minutes.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, mind_kit, scripting, sketch, toon, toon_everyday, toon_house, toon_props, toon_rooms
from srstudio import foley as synth
from srstudio.mind_kit import CARD, STAGE
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_everyday import Screen
from srstudio.toon_sketch import figure_group
from srstudio.voice import Voice, VoiceSettings

SEED = 3102
SLUG = "planning-fallacy"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "The Planning Fallacy — There's a Name for That"
NAME = "The Planning Fallacy"
DESCRIPTION = (
    "A pilot about how people think: a rabbit says five minutes from the shower, and the effect behind that promise "
    "is named, shown and tied to one study."
)
ACCESSIBILITY = (
    "A cartoon rabbit with shampoo on her head turns the shower off, says five minutes away into her phone, and turns "
    "it back on. A bear on a sofa gets the voice note at 7:05 and does not move. She says leaving now in a towel at "
    "7:32, almost ready at 7:44, and asks if she needs a jacket at 7:51. "
    "A card reads There's a name for that, The Planning Fallacy. Two bars "
    "set the plan against last time. A paper card sums up one study, and two bars show 33.9 days said against 55.5 "
    "days taken. The bear says the table is at 8:15, she says you said seven, and he says I know. The shower "
    "is running again."
)
NARRATION = "Voiced with ElevenLabs premade voices Daniel (narrator), Alice and Bill; synthesised effects."
NOTE = "ElevenLabs premade voices Daniel, Alice and Bill at their natural pace; no reference-voice cloning."

STUDY = mind_kit.Evidence(
    "Buehler, Griffin & Ross",
    "1994",
    "Thesis students, near the end, were phoned and asked when they'd finish.",  # Study 1, p. 369
    "Of 37 asked, the 33 who finished took far longer.",  # p. 369, Table 1 note: the means are on those 33
)
DAYS = 60.0  # days across the full bar: both bars to one scale
SAID = ("Average said, from that call", 33.9 / DAYS, "33.9 days")  # Study 1: p. 369, Table 1
TOOK = ("Average took, from that call", 55.5 / DAYS, "55.5 days")  # the same table
PLAN = ("The plan", 0.12, "shower, door")  # the mechanism's picture: the character's, not a measurement
PAST = ("Last time", 0.94, "shower, other shirt, keys")

DANIEL = Voice(role="narrator", id="onwK4e9ZLuTAKqWW03F9", name="Daniel")
NARRATOR = Speaker("narrator", DANIEL, VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15))
MIA = Speaker(
    "mia",
    Voice(role="mia", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "rabbit",
)
BRUNO = Speaker(
    "bruno",
    Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15),
    "bear",
)
TINTS = {"mia": mind_kit.SPOT, "bruno": mind_kit.SPOT, "narrator": mind_kit.INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-bear": 2, "toon-rabbit": 2}
FIGURES = {"rabbit": (1.2, 30.0), "bear": (1.1, -10.0)}

CLOCK = ("7:05", "7:32", "7:44", "7:51", "7:52")  # what the bear's lock screen says on each of his runs of shots
SENDER, HEARD = "MIA", "Voice note"
RECORDING = "Recording"
HAND = "#efe8ee"  # her coat: the thumb on her phone
HELD = {"at": (430.0, 760.0), "scale": 1.0, "hand": HAND}
PROPPED = {"at": (420.0, 826.0), "scale": 1.3}  # on the low table, and he leaves it there
MUG_X = 34.0
SUDS = {"at": (185.0, 452.0), "scale": 1.0}
TOWEL = {"at": (185.0, 462.0), "scale": 0.86}
DRY_FACE = (-30.0, 500.0)  # where the fall's foot stays clear so her face stays seen
SUDS_TOP = 300.0  # the water in that span lands here, on the shampoo
SMALL, SMALL_Y, SMALL_X = 0.46, 720.0, 540.0  # the rabbit under the bars: her foot on the plinth
BARS_Y = 520.0
PUSH_TO, PUNCH = 1.08, 1.16
PIVOT = (1000.0, 1000.0)  # this far right keeps both signature marks whole at PUNCH
END = 44.8

LINES = (
    Line("mia", "Five minutes away."),
    Line("mia", "Leaving now."),
    Line("mia", "Almost ready."),
    Line("mia", "Do I need a jacket?"),
    Line("narrator", "She means it."),
    Line("narrator", "There's a name for that."),
    Line("narrator", "The planning fallacy."),
    Line("narrator", "Saying a time, you mostly think of the plan."),
    Line("narrator", "Not last time."),
    Line("narrator", "Thesis students were asked when they'd finish."),
    Line("narrator", "They said about 34 days."),
    Line("narrator", "They took about 56."),
    Line("narrator", "Before you say a time, picture how it went the last few times"),
    Line("narrator", "and how this one could go the same way."),
    Line("narrator", "In a later study, the optimism went away."),
    Line("bruno", "The table is at 8:15."),
    Line("mia", "You said seven."),
    Line("bruno", "I know."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_card(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the card already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    hold(0.0, "rabbit", "", "wide", "grin", "desk"),  # the water running, on the frame the reel ends on
    say(0.4, "rabbit", 0, "wide", "grin", "desk", "off"),  # the tap off for the words, and for nothing else
    hold(1.8, "rabbit", "", "wide", "grin", "desk", "on"),
    hold(2.2, "bear", "", "half", "flat", "desk", "first"),
    say(4.4, "rabbit", 1, "wide", "grin", "desk", "dry"),
    hold(5.5, "bear", "", "half", "flat", "desk", "second"),
    say(7.6, "rabbit", 2, "up", "grin", "desk", "robe"),
    hold(8.7, "bear", "", "half", "flat", "desk", "third"),
    say(10.8, "rabbit", 3, "up", "flat", "desk", "hall"),
    hold(12.2, "bear", "", "half", "flat", "desk", "fourth"),
    say(14.4, "rabbit", 4, "wide", "grin", "desk"),
    on_card(say(15.5, CARD, 5, "wide", "flat", "desk", "name")),
    on_card(say(17.0, CARD, 6, "wide", "flat", "desk", "reveal")),
    say(18.4, STAGE, 7, "half", "flat", "desk", "plan"),
    say(20.9, STAGE, 8, "half", "flat", "desk", "past"),
    on_card(say(22.0, CARD, 9, "wide", "flat", "desk", "study")),
    on_card(say(24.8, CARD, 10, "wide", "flat", "desk", "said")),
    on_card(say(26.8, CARD, 11, "wide", "flat", "desk", "took")),
    say(28.9, "bear", 12, "half", "flat", "desk", "turn"),
    say(32.9, "bear", 13, "half", "flat", "desk"),
    say(35.4, "bear", 14, "half", "flat", "desk"),
    say(38.4, "bear", 15, "half", "flat", "desk", "table"),
    say(40.1, "rabbit", 16, "shock", "flat", "desk", "seven"),
    hold(41.4, "bear", "", "half", "flat", "desk", "punch"),
    say(42.6, "bear", 17, "half", "smirk", "desk"),
    hold(43.3, "rabbit", "", "wide", "grin", "desk", "again"),  # the water again, and the first frame comes round
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, MIA, BRUNO), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = (
    "off", "on", "first", "dry", "second", "robe", "third", "hall", "fourth", "name", "reveal", "plan", "past", "study",
    "said", "took", "turn", "table", "seven", "punch", "again",
)  # fmt: skip


def _screens() -> tuple[str, ...]:
    return (*CLOCK, SENDER, HEARD, RECORDING)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the opening is the behaviour with its line, and
    no word on screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sketch.events(sk.beats, "off")[0][0] >= 2.0:
        raise sketch.SketchError("the reel opens on the behaviour, with its line inside two seconds")
    if not 0 < sk.end <= 45.0:
        raise sketch.SketchError("a pilot runs at most 45 seconds")
    for text in (
        *(q.text for q in sk.lines),
        NAME,
        STUDY.what,
        STUDY.result,
        SAID[0],
        TOOK[0],
        PLAN[0],
        PLAN[2],
        PAST[0],
        PAST[2],
        *_screens(),
        POST.title,
        POST.description,
    ):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def _timed(shot, start: float, end: float):
    """A group of the shot's back for one set inside a shot of the same character."""
    return mind_kit.far(shot.cv, shot.cv.group(shot.back, shot.cv.uid("g"), start=start, end=end))


def _held(shot, speaks: float | None) -> None:
    """The phone in her hand, held clear of the water: dark, and recording from ``speaks`` when she does."""
    cv = shot.cv
    screens = (Screen(0.0, "off"), *(() if speaks is None else (Screen(speaks, "loading", RECORDING),)))
    toon_everyday.phone(cv, shot.front, screens, measure=shot.measure, id=cv.uid("phone"), **HELD)


def _bathroom(shot, worn, water: tuple[tuple[float, float], ...], speaks: float | None) -> None:
    """Her in the shower, or out of it: the tile, what is on her head, the water when it runs, the bath's rim."""
    cv = shot.cv
    toon_house.bathroom(cv, _timed(shot, shot.app.start, shot.app.end))
    mind_kit.key(cv, shot.light)
    worn(cv, figure_group(cv, shot.front, FIGURES["rabbit"]), id=cv.uid("worn"))
    if water:
        toon_house.shower_water(cv, shot.front, water, clear=DRY_FACE, stop=SUDS_TOP, id=cv.uid("water"))
    _held(shot, speaks)
    toon_house.ledge(cv, shot.front, "white")


def _soaped(cv, parent, id: str) -> None:
    toon_house.suds(cv, parent, id=id, **SUDS)


def _wrapped(cv, parent, id: str) -> None:
    toon_house.towel(cv, parent, id=id, **TOWEL)


def _hall(shot) -> None:
    cv = shot.cv
    toon_house.hallway(cv, _timed(shot, shot.app.start, shot.app.end), door="shut")
    mind_kit.key(cv, shot.light)
    _held(shot, shot.app.start + 0.1)
    toon_house.ledge(cv, shot.front, "oak")


def _bedroom(shot) -> None:
    """Still in the towel, a room further on."""
    cv = shot.cv
    toon_house.bedroom(cv, _timed(shot, shot.app.start, shot.app.end))
    mind_kit.key(cv, shot.light)
    _wrapped(cv, figure_group(cv, shot.front, FIGURES["rabbit"]), id=cv.uid("worn"))
    _held(shot, shot.app.start + 0.1)
    toon_house.ledge(cv, shot.front, "oak")


def _lounge(shot, clock: str) -> None:
    """The bear on the sofa: the phone propped on the low table buzzes with the time on it, and he leaves it there."""
    cv, start, end = shot.cv, shot.app.start, shot.app.end
    toon_rooms.lounge(cv, _timed(shot, start, end), end=end, blink=False)
    mind_kit.key(cv, shot.light)
    screens = (Screen(0.0, "off"), Screen(start + 0.1, "notify", SENDER, HEARD, clock))
    toon_house.ledge(cv, shot.front, "oak")
    toon_props.mug(cv, shot.front, MUG_X, steam=((start, end),))
    toon_everyday.phone(cv, shot.front, screens, measure=shot.measure, id=cv.uid("phone"), **PROPPED)


def dress(shot) -> None:
    """Every shot's set and props: the shower, the bath in a towel and the hall for her, the lounge for him, the stage
    for the name, the mechanism and the evidence."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    if app.who == CARD and app.end <= at["plan"]:
        mind_kit.stage(cv, shot.back)
        mind_kit.name_card(cv, shot.front, NAME, app.start, at["reveal"], app.end, shot.measure, id=cv.uid("name"))
        mind_kit.sign(cv, shot.front)
    elif app.who == CARD:
        mind_kit.stage(cv, shot.back)
        mind_kit.evidence_card(
            cv, shot.front, STUDY, app.start, app.end, shot.measure, id=cv.uid("study"), reveal=at["took"]
        )
        mind_kit.two_lines(
            cv,
            shot.front,
            SAID,
            TOOK,
            at["said"],
            app.end,
            shot.measure,
            reveal=at["took"],
            y=1000.0,
            id=cv.uid("bars"),
        )
        mind_kit.sign(cv, shot.front)
    elif app.who == STAGE:
        mind_kit.stage(cv, shot.back)
        mind_kit.two_lines(
            cv, shot.front, PLAN, PAST, app.start, app.end, shot.measure, reveal=at["past"], y=BARS_Y, id=cv.uid("bars")
        )
        g = cv.group(shot.back, cv.uid("g"), x=SMALL_X - SMALL * toon.fx(165), y=SMALL_Y, scaleX=SMALL, scaleY=SMALL)
        poses = toon.parse_poses([{"start": 0.0, "eyes": "up", "mouth": "flat", "arms": "desk"}], "under the bars")
        sketch.drawer("rabbit", shot.versions)(cv, g, poses, app.end, (), enter=app.start)
        mind_kit.floor(cv, shot.front)
    elif app.who == "rabbit" and app.start < at["first"]:
        _bathroom(shot, _soaped, ((0.0, at["off"]), (at["on"], app.end)), at["off"])
    elif app.who == "rabbit" and app.start == at["dry"]:
        _bathroom(shot, _wrapped, (), at["dry"] + 0.1)
    elif app.who == "rabbit" and app.start == at["robe"]:
        _bedroom(shot)
    elif app.who == "rabbit" and app.start == at["again"]:
        _bathroom(shot, _soaped, ((app.start, app.end),), None)
    elif app.who == "rabbit":
        _hall(shot)
    elif app.start < at["dry"]:
        _lounge(shot, CLOCK[0])
    elif app.start < at["robe"]:
        _lounge(shot, CLOCK[1])
    elif app.start < at["hall"]:
        _lounge(shot, CLOCK[2])
    elif app.start < at["table"]:
        _lounge(shot, CLOCK[3])
    else:
        _lounge(shot, CLOCK[4])


def lens(shot, setup) -> None:
    """A slow push on the bear through the turn, a punch-in on the hold before "I know."; everything else holds."""
    at = {name: sketch.events(shot.beats, name)[0][0] for name in ("turn", "punch")}
    if shot.app.start == at["turn"]:
        camera.anchor(setup, *PIVOT, place=True)
        camera.push_in(shot.cv, setup, scale=[(at["turn"], 1.0), (shot.app.end, PUSH_TO)])
    elif shot.app.start == at["punch"]:
        camera.anchor(setup, *PIVOT, place=True)
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (at["punch"], PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The channel's sting on the name, the shower that stops for the words, and a buzz as each voice note lands."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    times = {name: sketch.events(beats, name)[0][0] for name in ("off", "on", "first", "reveal", "again")}
    first = sketch.events(beats, "first")[0][0]
    buzz = [sketch.events(beats, name)[0][0] + 0.1 for name in ("first", "second", "third", "fourth")]
    sting = mind_kit.write_sting(audio / "sting.wav", [times["reveal"]], end)
    water = synth.write_water(
        audio / "water.wav", [(0.0, times["off"]), (times["on"], first), (times["again"], end)], end, seed=seed
    )
    note = synth.write_buzz(audio / "buzz.wav", buzz, end)
    return [
        sketch.effect("sting", 0.0, -5.0, root, sting),
        sketch.effect("water", 0.0, -16.0, root, water),
        sketch.effect("buzz", 0.0, -14.0, root, note),
    ]


POST = InstagramPost(
    title="She has been five minutes away since seven.",
    description=(
        "The planning fallacy: when people say a time, they mostly talk about the plan and rarely about the past. "
        "Thesis students phoned near the end said about 34 days from that call and took about 56 (37 surveyed; "
        "averages from the 33 who had finished). When students pictured how a job could go as usual, the optimism "
        "went away. They did not finish any sooner.\n"
        "Source: Buehler, Griffin & Ross (1994), Journal of Personality and Social Psychology 67(3)."
    ),
    credit="Voices: ElevenLabs premade voices Daniel, Alice and Bill. Original characters, drawn in code.",
    hashtags=("#psychology", "#planningfallacy", "#howpeoplethink", "#everydaylife"),
    thumbnail=Thumbnail(
        "Five minutes\naway.", 1.0, "There's a name for that", focus=(540.0, 760.0), zoom=1.0, place="bottom"
    ),
)
