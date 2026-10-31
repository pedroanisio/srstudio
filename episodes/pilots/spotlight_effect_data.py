"""The Spotlight Effect — a pilot of "There's a Name for That", main trigger recognition: the sketch as data.

One embarrassing shirt. A hamster has held a clipboard over it since breakfast and walks to the printer sideways. "It
was a gift," she tells a goat. "What was?" There's a name for that. Then why, and one study. People notice you less
than you think. And the goat, who has been holding his own clipboard up all along, lowers it: the same shirt, the same
words, in the same kitchen, so the end cuts back to the first frame.

Text on screen carries every key point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade
Bella; the two characters are ElevenLabs premade River and Bill. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen against
:func:`srstudio.mind_kit.check_copy`; :func:`dress` draws each shot and :func:`foley` its sound.

Every word and figure about the study lives in :data:`STUDY`, :data:`GUESSED` and :data:`COULD` and traces to
``pilots/mind/spotlight-effect/sources.md``: Study 1, 46% predicted and 23% actual, "exactly twice as high", and what
was measured is whether the room could say who was on the shirt. A shirt in a room is what was tested; the portrait
is invented, and how long she has worried is the character's feeling, which no line says the study measured.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    mind_kit,
    scripting,
    sketch,
    toon,
    toon_everyday,
    toon_head,
    toon_house,
    toon_rigs,
    toon_sets,
)
from srstudio import foley as synth
from srstudio.mind_kit import CARD, STAGE
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_sketch import SEAT, figure_group
from srstudio.voice import Voice, VoiceSettings

SEED = 3101
SLUG = "spotlight-effect"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "The Spotlight Effect — There's a Name for That"
NAME = "The Spotlight Effect"
DESCRIPTION = (
    "A pilot about how people think: a hamster hides one embarrassing shirt, and the effect behind that feeling is "
    "named, shown and tied to one study."
)
ACCESSIBILITY = (
    "A cartoon hamster looks down at her loud T-shirt, printed with a moustached potato in a heart, then holds a "
    "clipboard over it at her desk. She tells a goat it was a gift and he asks what was. A card reads There's a name "
    "for that, The Spotlight Effect. A beam of light picks her out, then splits into one beam for each character. A "
    "paper card sums up one study, and two bars show 46 percent guessed against 23 percent who could say who was on "
    "the shirt. She lowers the clipboard. The goat lowers his, wearing the same shirt, and looks down at it in the "
    "kitchen as she did."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator), River and Bill; synthesised effects."
NOTE = "ElevenLabs premade voices Bella, River and Bill at their natural pace; no reference-voice cloning."

STUDY = mind_kit.Evidence(
    "Gilovich, Medvec & Savitsky",
    "2000",
    "In one study, students wore an embarrassing T-shirt into a room.",
    "Their guess was double the real number.",
)
GUESSED = ("Guessed could say who was on it", 0.46, "46%")  # Study 1: p. 215, footnote 3
COULD = ("Really could", 0.23, "23%")  # the same footnote; each bar is its share of the room

NARRATOR = mind_kit.NARRATOR
HAMSTER = Speaker(
    "ham",
    Voice(role="ham", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "hamster",
)
GOAT = Speaker(
    "goat",
    Voice(role="goat", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.25),
    "goat",
)
TINTS = {"ham": mind_kit.SPOT, "goat": mind_kit.SPOT, "narrator": mind_kit.INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-hamster": 1, "toon-goat": 1, "toon-fox": 2}
FIGURES = {"hamster": (1.35, 0.0), "goat": (1.1, 0.0)}

SHIRT = {"hamster": 0.72, "goat": 0.66}  # its size on the figure: drawn in the figure's coordinates, it scales with it
BOARD_FIELDS = (toon_everyday.Field("Agenda"), toon_everyday.Field("Notes"))
PAW = {"hamster": "#f2a7a0", "goat": "#a083d8"}
BOARD = {"hamster": {"foot": 866, "scale": 1.0}, "goat": {"foot": 852, "scale": 1.1}}  # held over the chest and shirt
ROW_GOAT = 205
ROW = {"hamster": 530, "goat": ROW_GOAT, "fox": 845}  # the row's order, screen x of each figure
ROW_SCALE, ROW_Y, ROW_FOOT = 0.56, 560.0, 1405.0  # the row of people on the stage
ROW_BOARD = {"foot": 868, "scale": 1.2}  # at this size its smallest lettering still holds its contrast on screen
BEAM_FOOT = 1420.0
PUNCH, PIVOT = 1.14, (880.0, 1000.0)  # the pivot this far right keeps the code in frame
END = 39.6

LINES = (
    Line("narrator", "One embarrassing shirt."),
    Line("narrator", "You have held this clipboard since breakfast."),
    Line("narrator", "You walk to the printer sideways."),
    Line("narrator", "You have rehearsed saying it was a gift."),
    Line("goat", "Morning."),
    Line("ham", "It was a gift."),
    Line("goat", "What was?"),
    Line("narrator", "There's a name for that."),
    Line("narrator", "The spotlight effect."),
    Line("narrator", "You are the center of your own attention."),
    Line("narrator", "So you assume you are the center of everyone's."),
    Line("narrator", "That beam comes from being you."),
    Line("narrator", "In one study, students wore an embarrassing T-shirt into a room."),
    Line("narrator", "They guessed about half the room could say who was on it."),
    Line("narrator", "About a quarter could."),
    Line("narrator", "People notice you less than you think."),
    Line("narrator", "One embarrassing shirt."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_card(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the card already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    say(0.0, "hamster", 0, "down", "frown", "desk"),  # already looking down at it, in the kitchen
    say(1.8, "hamster", 1, "side", "flat", "desk", "desk"),  # at her desk, the clipboard up
    say(4.3, "hamster", 2, "side", "frown", "desk"),
    say(6.5, "hamster", 3, "up", "flat", "desk"),  # the rehearsal her next line pays off
    say(8.7, "goat", 4, "half", "flat", "desk"),
    say(9.9, "hamster", 5, "wide", "grin", "desk", wear=("flush",)),
    say(11.1, "goat", 6, "half", "flat", "desk", "punch"),
    hold(12.0, "goat", "", "half", "flat", "desk"),  # the silence is the laugh
    hold(12.7, "hamster", "", "shock", "flat", "desk", wear=("flush",)),
    on_card(say(13.7, CARD, 7, "wide", "flat", "desk", "name")),
    on_card(say(15.3, CARD, 8, "wide", "flat", "desk", "reveal")),
    say(17.5, "hamster", 9, "up", "flat", "desk", "beam"),
    say(20.1, STAGE, 10, "half", "flat", "desk"),
    say(22.5, STAGE, 11, "half", "flat", "desk", "split"),
    on_card(say(24.75, CARD, 12, "wide", "flat", "desk", "study")),
    on_card(say(28.4, CARD, 13, "wide", "flat", "desk", "guess")),
    on_card(say(31.2, CARD, 14, "wide", "flat", "desk", "real")),
    say(33.2, "hamster", 15, "side", "smirk", "desk", "lower"),
    hold(35.2, "goat", "", "side", "flat", "desk", "drop"),
    say(36.6, "goat", 16, "down", "frown", "desk", "kitchen"),  # the same frame as the first, and the same shirt
    hold(38.2, "goat", "", "down", "frown", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, HAMSTER, GOAT), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = ("desk", "punch", "name", "reveal", "beam", "split", "study", "guess", "real", "lower", "drop", "kitchen")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, and no word on
    screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the behaviour, with its line")
    for text in (
        *(q.text for q in sk.lines),
        NAME,
        STUDY.what,
        STUDY.result,
        GUESSED[0],
        COULD[0],
        POST.title,
        POST.description,
    ):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def _timed(shot, start: float, end: float):
    """A group of the shot's back for one set inside a shot of the same character."""
    return mind_kit.far(shot.cv, shot.cv.group(shot.back, shot.cv.uid("g"), start=start, end=end))


def _board(shot, start: float, end: float, lowered: float | None = None) -> None:
    """The clipboard held square over the shirt, on the framed figure's chest, sliding down out of the frame at
    ``lowered``. It is at screen scale, so it stays outside the figure's group: a clipboard has a minimum size."""
    cv, who = shot.cv, shot.app.who
    scale, dx = FIGURES[who]
    middle = SEAT[0] + dx + scale * (_chest(shot, who)[0] - SEAT[0])
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end, y=0.0)
    toon_everyday.clipboard(
        cv,
        g,
        "NOTES",
        BOARD_FIELDS,
        measure=shot.measure,
        id=cv.uid("board"),
        hand=PAW[who],
        at=(middle, BOARD[who]["foot"]),
        scale=BOARD[who]["scale"],
    )
    if lowered is not None:
        cv.keys(g, "y", [(lowered, 0.0), (lowered + 0.35, toon.fh(420))], kind="cubic-in", local=False)


def _chest(shot, who: str) -> tuple[float, float]:
    """Where ``who``'s chest is in the figure's own reference pixels, whatever the shot does to the figure."""
    return toon_head.chest(toon_rigs.rig_of(sketch.part_of(who), shot.versions))


def _shirt(shot, figure, who: str) -> None:
    """The shirt on ``who``, into ``figure``: a group with the transform that figure is drawn at."""
    toon_house.tee(shot.cv, figure, at=_chest(shot, who), scale=SHIRT[who], id=shot.cv.uid("tee"))


def _worn(shot, parent, who: str) -> None:
    """The shirt on the shot's framed character: the same scale and pivot as the figure it sits on."""
    _shirt(shot, figure_group(shot.cv, parent, FIGURES[who]), who)


def _kitchen_shot(shot, start: float, end: float) -> None:
    """The first frame, and the last: the office kitchen, and the shirt being looked at."""
    cv = shot.cv
    toon_sets.kitchen(cv, _timed(shot, start, end))
    _worn(shot, cv.group(shot.front, cv.uid("g"), start=start, end=end), shot.app.who)


def _others(shot, split: float, end: float) -> None:
    """The room's other people, in a row on the stage, each lit by their own beam once it splits."""
    cv = shot.cv
    for who, x in ROW.items():
        g = cv.group(
            shot.back, cv.uid("g"), x=x - ROW_SCALE * toon.fx(165), y=ROW_Y, scaleX=ROW_SCALE, scaleY=ROW_SCALE
        )
        poses = toon.parse_poses([{"start": 0.0, "eyes": "down", "mouth": "flat", "arms": "desk"}], "the row")
        sketch.drawer(who, shot.versions)(cv, g, poses, end, (), enter=shot.app.start)
        if who in SHIRT:
            _shirt(shot, g, who)
        mind_kit.spotlight(cv, shot.front, (x, ROW_FOOT), split, end, radius=130.0, id=cv.uid("beam"))
    # he has held it all along, here too; in front of the beams, which would dim its lettering
    held = cv.group(
        shot.front, cv.uid("g"), x=ROW_GOAT - ROW_SCALE * toon.fx(165), y=ROW_Y, scaleX=ROW_SCALE, scaleY=ROW_SCALE
    )
    toon_everyday.clipboard(
        cv,
        held,
        "NOTES",
        BOARD_FIELDS,
        measure=shot.measure,
        id=cv.uid("board"),
        hand=PAW["goat"],
        at=(_chest(shot, "goat")[0], ROW_BOARD["foot"]),
        scale=ROW_BOARD["scale"],
    )


def dress(shot) -> None:
    """Every shot's set and props: the kitchen and the desk for the behaviour, the stage for the name, the mechanism and
    the evidence, the desk again for the turn, and the kitchen for the last frame."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    if app.who not in (CARD, STAGE) and app.start != at["beam"]:
        mind_kit.key(cv, shot.light)
    if app.who == CARD and app.end <= at["beam"]:
        mind_kit.stage(cv, shot.back)
        mind_kit.name_card(cv, shot.front, NAME, app.start, at["reveal"], app.end, shot.measure, id=cv.uid("name"))
        mind_kit.sign(cv, shot.front)
    elif app.who == CARD:
        mind_kit.stage(cv, shot.back)
        mind_kit.evidence_card(
            cv, shot.front, STUDY, app.start, app.end, shot.measure, id=cv.uid("study"), reveal=at["real"]
        )
        mind_kit.two_lines(
            cv, shot.front, GUESSED, COULD, at["guess"], app.end, shot.measure, reveal=at["real"], y=1000.0
        )
        mind_kit.sign(cv, shot.front)
    elif app.who == STAGE:
        mind_kit.stage(cv, shot.back)
        mind_kit.floor(cv, shot.front)
        mind_kit.spotlight(cv, shot.front, (530.0, ROW_FOOT), app.start, at["split"], radius=260.0, id=cv.uid("beam"))
        _others(shot, at["split"], app.end)
    elif app.who == "hamster" and app.start == 0.0:
        _kitchen_shot(shot, 0.0, at["desk"])
        toon.room(cv, _timed(shot, at["desk"], app.end))
        _worn(shot, cv.group(shot.front, cv.uid("g"), start=at["desk"], end=app.end), "hamster")
        _board(shot, at["desk"], app.end)
        toon_house.ledge(cv, shot.front, "oak")
    elif app.who == "hamster" and app.start < at["beam"]:
        toon.room(cv, _timed(shot, app.start, app.end))
        _worn(shot, shot.front, "hamster")
        _board(shot, app.start, app.end)
        toon_house.ledge(cv, shot.front, "oak")
    elif app.who == "hamster" and app.start == at["beam"]:
        mind_kit.stage(cv, shot.back)
        _worn(shot, shot.front, "hamster")
        mind_kit.floor(cv, shot.front)
        mind_kit.spotlight(cv, shot.front, (toon.fx(180), BEAM_FOOT), app.start, app.end, id=cv.uid("beam"))
    elif app.who == "hamster":
        toon.room(cv, _timed(shot, app.start, app.end))
        _worn(shot, shot.front, "hamster")
        _board(shot, app.start, app.end, lowered=at["lower"] + 0.3)
        toon_house.ledge(cv, shot.front, "oak")
    elif app.start < at["beam"]:
        toon.room(cv, _timed(shot, app.start, app.end))
        _worn(shot, shot.front, "goat")
        _board(shot, app.start, app.end)
        toon_house.ledge(cv, shot.front, "white")
    else:
        toon.room(cv, _timed(shot, app.start, at["kitchen"]))
        over = cv.group(shot.front, cv.uid("g"), start=app.start, end=at["kitchen"])
        _worn(shot, over, "goat")
        _board(shot, app.start, at["kitchen"], lowered=app.start + 0.3)
        _kitchen_shot(shot, at["kitchen"], app.end)
        toon_house.ledge(cv, shot.front, "white")


def lens(shot, setup) -> None:
    """A punch-in on the goat for "What is?"; everything else holds."""
    punch = sketch.events(shot.beats, "punch")[0][0]
    if shot.app.start <= punch < shot.app.end:
        camera.anchor(setup, *PIVOT, place=True)
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (punch, PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The channel's sting on the name, a soft whoosh as each clipboard goes down."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    times = {name: sketch.events(beats, name)[0][0] for name in ("reveal", "lower", "drop")}
    sting = mind_kit.write_sting(audio / "sting.wav", [times["reveal"]], end)
    slide = synth.write_whoosh(audio / "slide.wav", [times["lower"] + 0.3, times["drop"] + 0.3], end)
    return [sketch.effect("sting", 0.0, -5.0, root, sting), sketch.effect("slide", 0.0, -14.0, root, slide)]


POST = InstagramPost(
    title="You have held this clipboard since breakfast.",
    description=(
        "The spotlight effect: we expect others to notice us more than they do. In one study, students in an "
        "embarrassing T-shirt guessed 46% of the room could say who was on it. 23% could.\n"
        "Source: Gilovich, Medvec & Savitsky (2000), Journal of Personality and Social Psychology 78(2)."
    ),
    credit="Voices: ElevenLabs premade voices Bella, River and Bill. Original characters, drawn in code.",
    hashtags=("#psychology", "#spotlighteffect", "#howpeoplethink", "#everydaylife"),
    thumbnail=Thumbnail(
        "It was\na gift.", 1.0, "There's a name for that", focus=(350.0, 1020.0), zoom=1.25, place="top"
    ),
)
