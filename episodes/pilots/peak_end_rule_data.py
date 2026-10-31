"""The Peak-End Rule — a pilot of "There's a Name for That", main trigger utility: the sketch as data.

A raccoon gives a dinner five stars. The salad took an hour, the sloth brought a lobster nobody ordered, "How is
everything?" "Great, thanks." He paid market price, and with the bill came a mint. There's a name for that. Then why,
on the memory shelf, and one study, the cold water. Then the use, worded as a thing to try, and the sloth brings the
viewer a mint: the viewer has been sitting in the raccoon's seat for every one of his shots, and has waited too, so
the reel loops into "Five stars."

Text on screen carries every key point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade
Daniel; the two characters are ElevenLabs premade voices. ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks the events and every word on screen against :func:`srstudio.mind_kit.check_copy`; :func:`dress`
draws each shot and :func:`foley` its sound.

Every word and figure about the study lives in :data:`STUDY`, :data:`SHORT` and :data:`LONG` and traces to
``pilots/mind/peak-end-rule/sources.md``. The dinner is the comedy, not a finding: no line says a dinner was tested,
and the turn says so.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    look,
    mind_kit,
    scripting,
    sketch,
    toon,
    toon_dinner,
    toon_everyday,
    toon_head,
    toon_house,
    toon_props,
    toon_rigs,
    toon_sets,
)
from srstudio import foley as synth
from srstudio.mind_kit import CARD, STAGE
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_sketch import figure_group
from srstudio.voice import Voice, VoiceSettings

SEED = 3104
SLUG = "peak-end-rule"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "The Peak-End Rule — There's a Name for That"
NAME = "The Peak-End Rule"
DESCRIPTION = (
    "A pilot about how people think: a raccoon gives five stars to a terrible dinner because of a mint, and the rule "
    "behind that is named, shown and tied to one study."
)
ACCESSIBILITY = (
    "A cartoon raccoon in a restaurant booth beams at five stars on his phone. Before that, his salad took an hour, "
    "a sloth waiter brought a lobster he did not order, and asked how everything was. Great, thanks, says the raccoon. "
    "He paid market price, then a mint arrived and his eyes turned to hearts. A card reads There's a name for that, "
    "The Peak-End Rule. A shelf holds four files, the hour, the lobster, market price and the mint, and the last two "
    "slide up. A paper card sums up one study, with two bars for 60 and 90 seconds in cold water, and says 22 of 32 "
    "chose to repeat the longer one. A note on a fridge reads buy mints. The sloth sets a mint in front of the viewer "
    "and says thank you for waiting."
)
NARRATION = "Voiced with ElevenLabs premade voices Daniel (narrator), Brian and Charlie; synthesised effects."
NOTE = "ElevenLabs premade voices Daniel, Brian and Charlie; no reference-voice cloning."

STUDY = mind_kit.Evidence(
    "Kahneman, Fredrickson, Schreiber & Redelmeier",
    "1993",
    "32 male students held one hand in cold water, then the other.",  # p. 402: 32 male UC students
    "22 of 32 (69%) chose to repeat the longer one.",  # p. 403
)
SHORT = ("One hand", 60 / 90, "60 s")  # p. 402: 14 °C for 60 s; each bar is its share of the longer trial
LONG = ("Other hand, ends slightly warmer", 1.0, "90 s")  # pp. 402-403: the same 60 s, then 30 s rising

DANIEL = Voice(role="narrator", id="onwK4e9ZLuTAKqWW03F9", name="Daniel")
NARRATOR = Speaker("narrator", DANIEL, VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15))
SLOTH = Speaker(
    "sloth",
    Voice(role="sloth", id="nPczCjzI2devNBz1zQrb", name="Brian"),
    VoiceSettings(stability=0.70, similarity_boost=0.75, style=0.15, speed=0.7),
    "sloth",
)
RACCOON = Speaker(
    "raccoon",
    Voice(role="raccoon", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35),
    "raccoon",
)
TINTS = {"sloth": mind_kit.SPOT, "raccoon": mind_kit.SPOT, "narrator": mind_kit.INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-sloth": 1, "toon-raccoon": 2}
FIGURES = {"raccoon": (1.2, 0.0), "sloth": (1.2, 0.0)}

BOARD = ("LOBSTER", "MARKET\nPRICE")  # the set's own special: the dish he did not order was on the wall all along
FILES = ("The hour", "The lobster", "Market price", "The mint")
WORST, LAST = 2, 3
SHELF_Y = 1100.0
BARS_Y = 936.0  # under the card with its result, over the signature marks
TIE, TIE_UP = 0.8, 92.0  # its size on the figure, and how far over the chest: under the chin, in the ruff
PHONE_PAW = "#3a3f47"
PHONE_AT, PHONE_SCALE = (440, 752), 1.5
ASK = "How was your meal?"
NOTE_TEXT = "BUY MINTS"
DINNER_CLOCK = (482, 408)
MINT_AT, MINT_SCALE = (300, 818), 2.0
PAID = 0.84  # how long into his line the reader takes the money
LANDS = 1.0  # into his last line: in the pause, on "for waiting"
SECOND_FILE = 1.1  # after the worst moment, on "the last"
BEEP: tuple[synth.Glide, ...] = ((1760.0, 1760.0, 0.07), (1760.0, 1760.0, 0.07))
CHIME: tuple[synth.Glide, ...] = ((1567.98, 1567.98, 0.22),)
PUNCH, PIVOT = 1.12, (960.0, 1000.0)  # the pivot this far right keeps the code in frame
END = 44.95

LINES = (
    Line("narrator", "Five stars."),
    Line("narrator", "The salad took an hour."),
    Line("sloth", "Thank you... for waiting."),
    Line("raccoon", "I ordered the salad."),
    Line("sloth", "How is everything?"),
    Line("raccoon", "Great, thanks."),
    Line("narrator", "He paid market price."),
    Line("narrator", "Then, a mint."),
    Line("raccoon", "Lovely place."),
    Line("narrator", "There's a name for that."),
    Line("narrator", "The peak-end rule."),
    Line("narrator", "Looking back, you often reach for two files:"),
    Line("narrator", "the worst moment and the last."),
    Line("narrator", "The hour barely counts."),
    Line("narrator", "Thirty-two male students held a hand in cold water."),
    Line("narrator", "The other hand got the same, then thirty seconds slightly warmer."),
    Line("narrator", "Twenty-two of them chose to repeat the longer one."),
    Line("narrator", "Cold water isn't dinner, but it's worth a try:"),
    Line("narrator", "When you host, plan the last five minutes first."),
    Line("sloth", "Thank you... for waiting."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_card(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the card already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    say(0.0, "raccoon", 0, "wide", "grin", "desk"),  # already rating it, the shells and the wrapper in front of him
    say(1.4, "raccoon", 1, "half", "flat", "desk", "wait"),  # the same seat, an hour into the same dinner
    say(2.7, "sloth", 2, "sleepy", "flat", "desk", "serve"),
    say(4.7, "raccoon", 3, "down", "flat", "desk"),
    hold(5.9, "sloth", "", "sleepy", "flat", "desk"),  # he heard; nothing happens; that is the laugh
    say(7.1, "sloth", 4, "sleepy", "flat", "desk"),
    say(8.9, "raccoon", 5, "wide", "grin", "desk"),
    say(10.2, "raccoon", 6, "shock", "flat", "desk", "pay"),
    say(11.9, "raccoon", 7, "down", "flat", "desk", "mint"),
    say(14.2, "raccoon", 8, "hearts", "grin", "desk", "melt"),
    on_card(say(15.3, CARD, 9, "wide", "flat", "desk", "name")),
    on_card(say(16.7, CARD, 10, "wide", "flat", "desk", "reveal")),
    say(18.3, STAGE, 11, "wide", "flat", "desk"),
    say(21.2, STAGE, 12, "wide", "flat", "desk", "worst"),
    say(23.15, STAGE, 13, "wide", "flat", "desk", "dim"),
    on_card(say(24.7, CARD, 14, "wide", "flat", "desk", "study")),
    on_card(say(28.35, CARD, 15, "wide", "flat", "desk", "long")),
    on_card(say(32.3, CARD, 16, "wide", "flat", "desk", "result")),
    say(35.2, "raccoon", 17, "up", "flat", "desk", "fridge"),
    say(38.5, "raccoon", 18, "side", "smirk", "desk", "note"),
    say(41.3, "sloth", 19, "sleepy", "flat", "desk", "last"),
    hold(43.3, "sloth", "", "sleepy", "smirk", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, SLOTH, RACCOON), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = (
    "wait",
    "serve",
    "pay",
    "mint",
    "melt",
    "name",
    "reveal",
    "worst",
    "dim",
    "study",
    "long",
    "result",
    "fridge",
    "note",
    "last",
)


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
        *FILES,
        STUDY.what,
        STUDY.result,
        SHORT[0],
        LONG[0],
        ASK,
        NOTE_TEXT,
        *BOARD,
        "PAID",
        "TAP CARD",
        POST.title,
        POST.description,
    ):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def _at(shot) -> dict[str, float]:
    return {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}


def _booth(shot, start: float, end: float, lettering: bool = True) -> None:
    """The restaurant behind the figure and the cloth in front of it, for one stretch of a shot."""
    cv = shot.cv
    wall = mind_kit.far(cv, cv.group(shot.back, cv.uid("g"), start=start, end=end))
    toon_dinner.restaurant(cv, wall, BOARD, lettering=lettering)
    toon_dinner.table(cv, cv.group(shot.front, cv.uid("g"), start=start, end=end))


def _booth_light(shot) -> None:
    """The booth's light, over the figure and under the cloth: the shade from the left and the cloth's edge up the
    figure. The kit's warm pool sits where this set hangs its board, and washes the lettering the joke needs."""
    cv = shot.cv
    g = cv.group(shot.light, cv.uid("g"))
    look.pool(cv, g, "mind-off", "#2a1a4a88", -420, 500, 900, 1100, opacity=0.3)
    look.fade(cv, g, "mind-contact", "#2a1a4a66", toon.fy(801), toon.fy(801) - 60.0, cv.width)


def _laid(shot, start: float, end: float, items: tuple[tuple, ...]):
    """The dishes on the cloth, for one stretch of a shot."""
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    toon_dinner.dishes(cv, g, items, id=cv.uid("dish"))
    return g


def _rating(shot, start: float, end: float) -> None:
    """His phone, held up, the five stars filling: the behaviour, already happening."""
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    toon_everyday.phone(
        cv,
        g,
        (toon_everyday.Screen(0.0, "off"),),
        measure=shot.measure,
        at=PHONE_AT,
        scale=PHONE_SCALE,
        hand=PHONE_PAW,
        id=cv.uid("phone"),
    )
    x, y = toon.fx(PHONE_AT[0]), toon.fy(PHONE_AT[1])
    cv.text(
        g,
        cv.uid("rating"),
        ASK.replace(" your", "\nyour"),
        round(x - 150),
        round(y - 590),
        300,
        120,
        42,
        color=mind_kit.PAPER,
        wrap="none",
    )
    stars = (PHONE_AT[0], PHONE_AT[1] - 170)
    toon_everyday.stars(cv, g, 5, at=stars, start=start, step=0.12, scale=0.72, id=cv.uid("stars"))


def _waiter(shot) -> None:
    """The bow tie on the sloth: drawn in the figure's coordinates, so it holds at the shot's framing."""
    rig = toon_rigs.rig_of(sketch.part_of("sloth"), shot.versions)
    figure = figure_group(shot.cv, shot.front, FIGURES["sloth"])
    x, y = toon_head.chest(rig)
    toon_house.bow_tie(shot.cv, figure, (x, y - TIE_UP), TIE, id=shot.cv.uid("tie"))


def dress(shot) -> None:
    """Every shot's set and props: the booth for the dinner and the last frame, the stage for the name, the mechanism
    and the evidence, and his own kitchen for the use."""
    cv, app = shot.cv, shot.app
    at = _at(shot)
    if app.who == CARD and app.end <= at["worst"]:
        mind_kit.stage(cv, shot.back)
        mind_kit.name_card(cv, shot.front, NAME, app.start, at["reveal"], app.end, shot.measure, id=cv.uid("name"))
        mind_kit.sign(cv, shot.front)
    elif app.who == CARD:
        mind_kit.stage(cv, shot.back)
        mind_kit.evidence_card(
            cv, shot.front, STUDY, app.start, app.end, shot.measure, id=cv.uid("study"), reveal=at["result"]
        )
        mind_kit.two_lines(
            cv, shot.front, SHORT, LONG, app.start + 0.6, app.end, shot.measure, reveal=at["long"], y=BARS_Y
        )
        mind_kit.sign(cv, shot.front)
    elif app.who == STAGE:
        mind_kit.stage(cv, shot.back)
        mind_kit.memory_shelf(
            cv,
            shot.front,
            FILES,
            measure=shot.measure,
            pull=(WORST, at["worst"]),
            also=((LAST, at["worst"] + SECOND_FILE),),
            y=SHELF_Y,
            id=cv.uid("shelf"),
        )
        dimmed = cv.group(shot.front, cv.uid("g"), start=at["dim"], end=app.end)
        cv.rect(dimmed, 102, SHELF_Y - 380, 201, 380, mind_kit.INK, opacity=0.45, radius=12.0)
        mind_kit.sign(cv, shot.front)
    elif app.who == "raccoon" and app.end <= at["serve"]:
        _booth_light(shot)
        _booth(shot, app.start, at["wait"], lettering=False)  # the phone stands in front of the board
        _booth(shot, at["wait"], app.end)
        _laid(shot, app.start, at["wait"], (("shells", 150),))
        toon_dinner.mint(cv, cv.group(shot.front, cv.uid("g"), start=app.start, end=at["wait"]), (300, 826), eaten=True)
        _rating(shot, app.start, at["wait"])
        _laid(shot, at["wait"], app.end, (("water", 150),))
        wall = cv.group(shot.back, cv.uid("g"), start=at["wait"])
        jumps = ("07:10", "07:30", "07:50", "08:10")
        toon_props.clock(
            cv, wall, tuple((at["wait"] + 0.35 * k, time) for k, time in enumerate(jumps)), DINNER_CLOCK, 58
        )
    elif app.who == "raccoon" and app.end <= at["name"]:
        _booth_light(shot)
        _booth(shot, app.start, app.end)
        if app.start < at["pay"]:
            _laid(shot, app.start, at["pay"], (("water", 150), ("lobster", 320)))
        _laid(shot, at["pay"], at["mint"], (("shells", 150),))
        toon_dinner.card_reader(
            cv,
            cv.group(shot.front, cv.uid("g"), start=at["pay"], end=at["mint"]),
            ((0.0, "TAP CARD", "idle"), (at["pay"] + PAID, "PAID", "idle")),
            at=(400, 826),
            id=cv.uid("reader"),
        )
        toon_dinner.mint(
            cv, cv.group(shot.front, cv.uid("g"), start=at["mint"], end=app.end), MINT_AT, MINT_SCALE, id=cv.uid("mint")
        )
    elif app.who == "raccoon":
        mind_kit.key(cv, shot.light)
        toon_sets.kitchen(cv, mind_kit.far(cv, cv.group(shot.back, cv.uid("g"), start=app.start, end=app.end)))
        toon_house.ledge(cv, shot.front, "oak")
        toon_sets.note_insert(cv, shot.front, NOTE_TEXT, at["note"], app.end)
    elif app.start < at["fridge"]:  # the sloth, from the raccoon's seat
        _booth_light(shot)
        _booth(shot, app.start, app.end)
        _waiter(shot)
        _laid(shot, app.start, app.end, (("water", 150), ("lobster", 320)))
    else:  # the same framing, and now it is the viewer's table
        _booth_light(shot)
        _booth(shot, app.start, app.end)
        _waiter(shot)
        toon_dinner.mint(cv, shot.front, MINT_AT, MINT_SCALE, start=at["last"] + LANDS, id=cv.uid("mint"))


def lens(shot, setup) -> None:
    """A punch-in on the hearts; everything else holds."""
    melt = sketch.events(shot.beats, "melt")[0][0]
    if shot.app.start <= melt < shot.app.end:
        camera.anchor(setup, *PIVOT, place=True)
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (melt, PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The channel's sting on the name, the reader's beep, a bright note for each mint, a slide for each file."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    times = {name: sketch.events(beats, name)[0][0] for name in ("pay", "mint", "reveal", "worst", "last")}
    sting = mind_kit.write_sting(audio / "sting.wav", [times["reveal"]], end)
    beep = synth.write_tones(audio / "beep.wav", [times["pay"] + PAID], end, BEEP)
    chime = synth.write_tones(audio / "chime.wav", [times["mint"], times["last"] + LANDS], end, CHIME)
    slide = synth.write_whoosh(audio / "slide.wav", [times["worst"], times["worst"] + SECOND_FILE], end)
    return [
        sketch.effect("sting", 0.0, -5.0, root, sting),
        sketch.effect("beep", 0.0, -14.0, root, beep),
        sketch.effect("chime", 0.0, -8.0, root, chime),
        sketch.effect("slide", 0.0, -14.0, root, slide),
    ]


POST = InstagramPost(
    title="Five stars. For a mint.",
    description=(
        "The peak-end rule: we often judge an experience by its worst moment and its last, and how long it lasted "
        "barely counts. In one study, 22 of 32 male students chose to repeat the longer of two cold-water trials, the "
        "one that ended slightly warmer. Cold water isn't dinner, and for long holidays the evidence is much weaker, "
        "so treat it as a thing to try.\n"
        "Source: Kahneman, Fredrickson, Schreiber & Redelmeier (1993), Psychological Science 4(6)."
    ),
    credit="Voices: ElevenLabs premade voices Daniel, Brian and Charlie. Original characters, drawn in code.",
    hashtags=("#psychology", "#peakendrule", "#howpeoplethink", "#everydaylife"),
    thumbnail=Thumbnail("Five stars.\nFor a mint.", 1.0, "There's a name for that", place="bottom"),
)
