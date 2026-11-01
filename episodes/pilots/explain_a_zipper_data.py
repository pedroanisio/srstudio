"""Explain a Zipper — "There's a Name for That" #4, main trigger surprise: the sketch as data.

The observation: you know how a zipper works until someone says go on, then. So the claim comes first, on a zipper
being pulled, over a raccoon who has already rated himself seven out of seven on a whiteboard. A hedgehog asks him to
explain it, and a toilet, and a helicopter, and the board fills with what he says. The finding is the payoff: nearly
all of the people in the study marked themselves down. The raccoon follows them.

Every word about the study lives in :data:`HOW`, :data:`DOWN`, :data:`STAMP` and :data:`CITE` and traces to
``pilots/mind/explain-a-zipper/sources.md``. The scores on the board are the raccoon's, not the paper's.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, look, mind_kit, scripting, sketch, toon, toon_house, toon_props
from srstudio import foley as synth
from srstudio.mind_kit import INK, SPOT
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.voice import Voice, VoiceSettings

BLEED = True
SEED = 3704
SLUG = "explain-a-zipper"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
SERIES = "There's a Name for That #4"
TITLE = f"Explain a Zipper — {SERIES}"
NAME = "Illusion of explanatory depth"
DESCRIPTION = (
    "A pilot about how people think: a raccoon gives himself seven out of seven on zippers, then has to explain one."
)
ACCESSIBILITY = (
    "A zipper fills the frame and is pulled open on a raccoon at a whiteboard that reads zipper, seven out of seven. A "
    "hedgehog tells him to go on, then. He says it's a pulling situation. Asked about a toilet he says the water "
    "leaves, out of respect, and a helicopter is a fan, with confidence, and the board fills up with both. A stamp "
    "reads Nearly all of 16 students marked themselves down, Rozenblit & Keil, 2002. The hedgehog asks if it is still "
    "seven, and the raccoon says put him down for a two."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator), Charlie and Jessica; synthesised effects."
NOTE = "ElevenLabs premade voices Bella, Charlie and Jessica at their natural pace; no reference-voice cloning."

HOOK = "You don't know how a zipper works."
HOW = ("People rate how well they understand a thing.", "Then they have to explain it.")
DOWN = "Nearly all of them marked themselves down."
STAMP = ("Nearly all of 16 students", "marked themselves down.")
CITE = "Rozenblit & Keil, 2002"
LAST = "Put me down for a two."

NARRATOR = mind_kit.NARRATOR
RACCOON = Speaker(
    "raccoon",
    Voice(role="raccoon", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.40),
    "raccoon",
)
HEDGEHOG = Speaker(
    "hedgehog",
    Voice(role="hedgehog", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
    "hedgehog",
)
TINTS = {"raccoon": SPOT, "hedgehog": SPOT, "narrator": INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-raccoon": 2, "toon-hedgehog": 2}
HEADS = ("raccoon", "hedgehog")
FIGURES = {"raccoon": (1.25, -70.0), "hedgehog": (1.25, 40.0)}
ZIP_FROM, ZIP_TO = 0.4, 1.5  # seconds of the pull
BOARD_SIZE = 44
LEDGE = "oak"
PUNCH, PIVOT = 1.12, (700.0, 800.0)  # about the board, so the score stays in frame
THUD = synth.Burst(seconds=0.2, low_hz=320.0, decay=0.3, tone_hz=120.0, tone_end_hz=60.0, tone=0.8)
END = 24.4

LINES = (
    Line("narrator", HOOK),
    Line("raccoon", "I do. Seven out of seven."),
    Line("hedgehog", "Go on, then."),
    Line("raccoon", "So. The teeth. It's a pulling situation."),
    Line("narrator", HOW[0]),
    Line("narrator", HOW[1]),
    Line("hedgehog", "And a toilet?"),
    Line("raccoon", "The water leaves. Out of respect."),
    Line("hedgehog", "A helicopter?"),
    Line("raccoon", "It's a fan. With confidence."),
    Line("narrator", DOWN),
    Line("hedgehog", "Still seven?", gain=-3.0),
    Line("raccoon", LAST),
)
EVENTS = ("zipper", "pulling", "toilet", "fan", "stamp", "still", "two", "named")

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_stamp(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the stamp already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    say(0.0, "raccoon", 0, "half", "flat", "desk"),
    say(2.0, "raccoon", 1, "half", "grin", "desk", "zipper"),
    say(4.0, "hedgehog", 2, "half", "flat", "desk"),
    say(5.0, "raccoon", 3, "side", "open", "desk", "pulling"),
    say(8.0, "raccoon", 4, "up", "flat", "desk"),
    say(10.2, "raccoon", 5, "up", "flat", "desk"),
    say(12.0, "hedgehog", 6, "half", "flat", "desk"),
    say(13.2, "raccoon", 7, "half", "grin", "desk", "toilet"),
    say(15.4, "hedgehog", 8, "half", "flat", "desk"),
    say(16.4, "raccoon", 9, "half", "grin", "desk", "fan"),
    on_stamp(say(18.5, "raccoon", 10, "down", "flat", "desk", "stamp")),
    say(20.6, "hedgehog", 11, "half", "flat", "desk", "still"),
    say(21.6, "raccoon", 12, "side", "flat", "desk", "two"),
    hold(23.0, "raccoon", "", "closed", "flat", "desk", "named"),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, RACCOON, HEDGEHOG), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
BOARD = (
    ("ZIPPER 7/7", "pulling"),
    ("TEETH: PULLING", "toilet"),
    ("TOILET: IT LEAVES", "fan"),
    ("HELICOPTER: FAN", "two"),
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the claim opens it, and no word on screen is
    one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line != 0 or sk.beats[0].start != 0.0:
        raise sketch.SketchError("the claim opens the reel")
    cover = (THUMBNAIL.headline, THUMBNAIL.kicker)
    board = tuple(text for text, _ in BOARD)
    for text in (*(q.text for q in sk.lines), *STAMP, CITE, NAME, *board, POST.title, POST.description, *cover):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own table: see :func:`dress`."""


def _board(shot, at: dict[str, float]) -> None:
    """What he has said so far, on the board behind him, and the score he ends on."""
    cv, app = shot.cv, shot.app
    words = cv.group(shot.back, cv.uid("g"))
    rows = [(at[stop], text) for text, stop in BOARD]
    start = 0.0
    for stop, text in rows:
        if max(start, app.start) < min(stop, app.end):
            toon_props.board_text(cv, words, text, BOARD_SIZE, max(start, app.start), min(stop, app.end))
        start = stop
    if max(start, app.start) < app.end:
        toon_props.board_text(cv, words, "ZIPPER 2/7", BOARD_SIZE, max(start, app.start), app.end)


def dress(shot) -> None:
    """Every shot in the room with the board, the stamp and the name over it, the zipper over the first."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    far = mind_kit.far(cv, shot.back)
    toon_props.meeting(cv, far)
    _board(shot, at)
    look.fade(cv, shot.light, "mind-contact", "#2a1a4a66", toon.fy(801), toon.fy(801) - 60.0, cv.width)
    toon_house.ledge(cv, shot.front, LEDGE, 46.0)
    if app.start <= at["stamp"] < app.end:
        mind_kit.stamp(cv, shot.front, STAMP, CITE, at["stamp"], app.end, shot.measure)
    if app.start <= at["named"] < app.end:
        mind_kit.named(cv, shot.front, NAME, at["named"], app.end, shot.measure, PUNCH, PIVOT)
    if app.start == 0.0:
        mind_kit.zipper(cv, shot.front, ZIP_FROM, ZIP_TO)


def lens(shot, setup) -> None:
    """Everything holds, and a punch on the two."""
    two = sketch.events(shot.beats, "two")[0][0]
    if shot.app.start <= two < shot.app.end:
        camera.anchor(setup, *PIVOT, place=True)
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (two, PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The zip, marker squeaks on what goes on the board, the stamp's thud, the sting, and a room that is otherwise
    quiet enough to hear him think."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = {name: sketch.events(beats, name)[0][0] for name in EVENTS}
    zips = [round(ZIP_FROM + k * 0.05, 3) for k in range(int((ZIP_TO - ZIP_FROM) / 0.05))]
    rows = {
        "zip": (synth.write_typing(audio / "zip.wav", zips, end, seed=seed), -8.0),
        "marker": (
            synth.write_typing(
                audio / "marker.wav", [at["pulling"], at["toilet"], at["fan"], at["two"]], end, seed=seed
            ),
            -14.0,
        ),
        "stamp": (synth.write_bursts(audio / "stamp.wav", [at["stamp"]], end, THUD, seed=seed), -6.0),
        "sting": (mind_kit.write_sting(audio / "sting.wav", [at["named"]], end), -9.0),
        "room": (synth.write_room(audio / "room.wav", end, seed=seed), -30.0),
    }
    return [sketch.effect(name, 0.0, gain, root, path) for name, (path, gain) in rows.items()]


THUMBNAIL = Thumbnail("Seven out\nof seven", 3.0, SERIES, place="bottom")
POST = InstagramPost(
    title="Could you actually explain a zipper?",
    description=(
        f"{SERIES}. The illusion of explanatory depth: in Rozenblit & Keil's first study, nearly all of 16 Yale "
        "graduate students rated their understanding of everyday devices lower after trying to explain them. "
        "Small university "
        "samples, about how things work; the drop was absent or small for procedures, stories and facts. The scores on "
        "the board are ours.\n"
        "Source: Rozenblit & Keil (2002), Cognitive Science"
    ),
    credit="Voices: ElevenLabs premade voices Bella, Charlie and Jessica. Original characters, drawn in code.",
    hashtags=("#psychology", "#explanatorydepth", "#howpeoplethink", "#zipper"),
    thumbnail=THUMBNAIL,
)
