"""Choice Blindness — a pilot of "There's a Name for That", main trigger surprise, the finding up front: the sketch as
data.

The observation: hand someone a thing they didn't pick and they will tell you why it was the obvious choice. So the
claim comes first, a goat orders vanilla, and a fox hands him mint behind the counter. "Why mint?" "Vanilla's for
cowards." The fox swaps it again while his eyes are shut, for a cone of toothpaste, and asks again. He takes a breath,
and the last reason is the line the reel exists for: "Vanilla has never once protected my enamel."

Text on screen carries every key point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade
Bella; the two characters are ElevenLabs premade George and Callum. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen against
:func:`srstudio.mind_kit.check_copy`; :func:`dress` draws each shot and :func:`foley` its sound.

Every word about the study lives in :data:`HOOK`, :data:`STAMP`, :data:`SOURCE` and :data:`TURN` and traces to
``pilots/mind/choice-blindness/sources.md``. The figure is swaps, not people, and the study is photos of faces: the
ice cream is fiction with no study attached, and the goat's reasons carry no number. Only 13.3% of explanations cited
something only the swapped choice had, so no line says that is typical. Nobody in the sketch challenges him, because
nobody in the studies was challenged.
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
    toon_cars,
    toon_cast,
    toon_critters,
    toon_house,
    toon_parlour,
    toon_rigs,
)
from srstudio import foley as synth
from srstudio.mind_kit import CORAL, INK, PAPER, SPOT
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_cars import Passing
from srstudio.voice import Voice, VoiceSettings

SEED = 3701
SLUG = "choice-blindness"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Choice Blindness — There's a Name for That"
NAME = "Choice blindness"
DESCRIPTION = (
    "A pilot about how people think: a goat orders vanilla, is handed something else twice, and explains why that is "
    "what he chose."
)
ACCESSIBILITY = (
    "A cartoon goat stands at the counter of a pink ice cream parlour and orders vanilla. Behind the counter a fox "
    "lowers the vanilla cone out of sight and raises a mint one. The goat explains why he chose mint. A stamp reads "
    "Only 13% of swaps spotted at the time, Johansson et al., 2005. While the goat licks with his eyes shut, the "
    "fox's arm swaps his cone for a cone of striped toothpaste with the tube stuck in it. He tastes it, foam at his "
    "mouth, is asked why toothpaste, and explains that too, with passion."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator), George and Callum; synthesised effects."
NOTE = "ElevenLabs premade voices Bella, George and Callum at their natural pace; no reference-voice cloning."

HOOK = "Most people will explain a choice they never made."
STAMP = ("Only 13% of swaps", "spotted at the time.", "Johansson et al., 2005")
SAID = "Only thirteen percent of swaps were spotted at the time."
SOURCE = "Johansson et al. (2005), Science"
TURN = ("When we explain a choice,", "we may be building the reason, not remembering it.")
LAST = "Vanilla has never once protected my enamel."

NARRATOR = mind_kit.NARRATOR
GOAT = Speaker(
    "goat",
    Voice(role="goat", id="JBFqnCBsd6RMkjVDRZzb", name="George"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "goat",
)
FOX = Speaker(
    "fox",
    Voice(role="fox", id="N2lVS1w4EtoT3dr4eOWO", name="Callum"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.15),
    "fox",
)
TINTS = {"goat": SPOT, "fox": SPOT, "narrator": INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-goat": 1, "toon-fox": 2}
HEADS = ("goat", "fox")
FIGURES = {"goat": (1.3, -5.0), "fox": (1.25, 150.0)}

GOAT_COAT, GOAT_HOOF, FOX_COAT, FOX_PAW = (
    toon_critters.GOAT.coat,
    toon_critters.GOAT_HOOF,
    toon_cast.FOX.coat,
    "#5a3024",
)
STAND_AT = ((362.0, 812.0), (456.0, 812.0))  # the two cones on the counter, points sunk in its edge
STAND_SCALE = 0.64
GOAT_ROOT, HAND = (255.0, 784.0), (445.0, 610.0)  # his arm starts where a resting hoof is, and covers it
FOX_ROOT, FOX_HAND = (296.0, 784.0), (160.0, 620.0)
LICK = -14.0  # degrees of arm that take the cone to his mouth
DOWN = -105.0  # degrees of arm that take a cone below the counter, away from him
SWING = 0.24  # seconds an arm takes down, or back up
SNEAK = 0.34  # seconds the fox's reach waits before the swap, and takes to leave after it
PUSH, PUNCH, PIVOT = 1.12, 1.22, (560.0, 800.0)  # the pivot is in frame pixels
MARKS_IN = 46.0  # the counter's signature marks, in far enough that the punch keeps them in frame
STAMP_SIZE, CITE_SIZE = 58.0, 36.0
STAMP_Y, STAMP_W, STAMP_H = 270.0, 700.0, 192.0
CITE_INK = "#8f2a16"  # coral dark enough to read on paper
BUBBLES = (
    (-44, 4, 11), (-34, 12, 12), (-46, 18, 10), (-36, 28, 11), (-30, 40, 7),  # his left corner, with a drip
    (40, 2, 11), (32, 12, 12), (46, 14, 10), (36, 24, 10),
)  # fmt: skip
THUD = synth.Burst(seconds=0.2, low_hz=320.0, decay=0.3, tone_hz=120.0, tone_end_hz=60.0, tone=0.8)
FOAM, FOAM_BLUE = "#f4fbff", "#54c6f2"
END = 25.05

LINES = (
    Line("narrator", HOOK),
    Line("goat", "Vanilla, please."),
    Line("fox", "Why mint?"),
    Line("goat", "Vanilla's for cowards."),
    Line("narrator", SAID),
    Line("fox", "Why toothpaste?"),
    Line("goat", "Why toothpaste?"),
    Line("narrator", TURN[0]),
    Line("narrator", TURN[1]),
    Line("goat", "I've been a toothpaste person for years."),
    Line("goat", LAST),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_stamp(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the stamp already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    say(0.0, "goat", 0, "side", "flat", "desk"),  # already weighing the two cones: the claim, over the choice
    say(2.6, "goat", 1, "side", "grin", "desk", "vanilla"),
    hold(3.6, "fox", "", "half", "flat", "desk", "swap"),  # down goes the vanilla, up comes the mint
    say(4.05, "fox", 2, "half", "flat", "desk"),
    say(4.95, "goat", 3, "half", "grin", "desk", "cowards"),
    on_stamp(say(6.35, "goat", 4, "closed", "tongue", "desk", "stamp")),  # eyes shut, so the fox can reach in
    replace(
        on_stamp(say(8.0, "goat", 4, "closed", "tongue", "desk", "sneak")), word=5
    ),  # on "were", still on the stamp
    hold(9.5, "goat", "", "down", "flat", "desk", "tasted"),
    say(10.6, "fox", 5, "half", "flat", "desk", "why"),
    say(11.85, "goat", 6, "wide", "open", "desk", "again"),
    say(13.0, "goat", 7, "side", "flat", "desk", "turn"),
    say(14.5, "goat", 8, "up", "flat", "desk"),
    replace(say(15.9, "goat", 8, "side", "flat", "desk"), word=6),  # on "not": he looks at what he is holding
    say(17.3, "goat", 9, "half", "grin", "desk", "years"),
    hold(19.5, "fox", "", "half", "flat", "desk", "blink"),
    say(20.95, "goat", 10, "wide", "open", "desk", "last"),
    hold(23.55, "goat", "", "half", "grin", "desk", "named"),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, GOAT, FOX), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = (
    "vanilla",
    "swap",
    "cowards",
    "stamp",
    "sneak",
    "tasted",
    "why",
    "again",
    "turn",
    "years",
    "blink",
    "last",
    "named",
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
    if sk.beats[0].line != 0 or sk.beats[0].start != 0.0:
        raise sketch.SketchError("the claim opens the reel")
    cover = (THUMBNAIL.headline, THUMBNAIL.kicker)
    for text in (*(q.text for q in sk.lines), *STAMP, NAME, POST.title, POST.description, *cover):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own counter: see :func:`dress`."""


def _traffic(app, at: dict[str, float]) -> tuple[Passing, ...]:
    """What goes by the window behind the goat, so the street keeps moving whatever he is doing."""
    plan = [
        Passing(1.0, "car", toon_cars.GREY),
        Passing(at["stamp"] + 0.4, "car", toon_cars.BODY),
        Passing(at["turn"] + 0.8, "bus"),
        Passing(at["years"] + 0.5, "car", "#ff8fa3"),
        Passing(at["last"] + 0.6, "car", toon_cars.GREY),
    ]
    return tuple(p for p in plan if app.start <= p.at < app.end)


def _contact(cv, parent) -> None:
    """The shade the counter's edge throws up the figure; the parlour stays bright, so there is no other light."""
    look.fade(cv, parent, "mind-contact", "#2a1a4a66", toon.fy(801), toon.fy(801) - 60.0, cv.width)


def _stand(shot) -> None:
    """The two cones he is choosing between, on the counter in front of him."""
    cv = shot.cv
    for at, flavour in zip(STAND_AT, toon_parlour.FLAVOURS, strict=True):
        toon_parlour.cone(cv, shot.front, at, flavour, STAND_SCALE)


def _goat_arm(shot, at: dict[str, float]) -> None:
    """His arm from the moment he has a cone: mint, then what the fox left him, swung up to his mouth for a lick."""
    cv, app = shot.cv, shot.app
    t = at["sneak"] + SNEAK
    spans = [(a, b, kind) for a, b, kind in ((app.start, t, "mint"), (t, app.end, "toothpaste")) if a < b]
    swings: tuple[tuple[float, float], ...] = ()
    if app.start <= at["stamp"] < app.end:
        a, b = at["stamp"], at["tasted"]
        swings = ((a, 0.0), (a + 0.4, LICK), (a + 0.9, 0.0), (b - 0.6, 0.0), (b - 0.1, LICK), (b + 0.4, 0.0))
    toon_parlour.held(cv, shot.front, spans, GOAT_ROOT, HAND, GOAT_COAT, GOAT_HOOF, app.start, app.end, swings=swings)


def _fox_arm(shot, at: dict[str, float]) -> None:
    """The fox's cone: the vanilla swings down behind the counter and the mint comes up on the same arm."""
    cv, app = shot.cv, shot.app
    if app.start <= at["swap"] < app.end:
        t = at["swap"] + 0.1
        swings = ((t, 0.0), (t + SWING, DOWN), (t + 2 * SWING, 0.0))
        spans = ((app.start, t + SWING, "vanilla"), (t + SWING, app.end, "mint"))
        toon_parlour.held(
            cv, shot.front, spans, FOX_ROOT, FOX_HAND, FOX_COAT, FOX_PAW, app.start, app.end, swings=swings
        )


def _sneak(shot, at: dict[str, float]) -> None:
    """The fox's arm in from the right with the toothpaste, out again with the mint, on the beat he cannot see."""
    cv = shot.cv
    t = at["sneak"] + SNEAK
    start, end = at["sneak"], t + SNEAK
    if not (shot.app.start <= start and end <= shot.app.end):
        return
    reach = 150.0
    x, y = HAND[0] + 96.0, HAND[1]
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    away = toon.fh(reach + 120.0)
    cv.keys(g, "x", [(start, away), (t - 0.08, 0.0), (t + 0.04, 0.0), (end, away)], hold=False, kind="cubic-in-out")
    cv.rect(g, toon.fx(x), toon.fy(y - 28), toon.fh(420), toon.fh(56), FOX_COAT, cv.ink, toon.INK_W, radius=toon.fh(26))
    toon_parlour.toothpaste_cone(cv, cv.group(g, cv.uid("g"), start=start, end=t), (x, y + 14.0))
    toon_parlour.cone(cv, cv.group(g, cv.uid("g"), start=t, end=end), (x, y + 14.0), "mint")
    cv.ellipse(g, toon.fx(x - 34), toon.fy(y - 34), toon.fh(68), toon.fh(68), FOX_PAW, cv.ink, toon.INK_W)


def _stamp(shot, at: dict[str, float]) -> None:
    """The evidence, stamped on the picture: one line and its source, gone when he tastes what the fox gave him."""
    cv = shot.cv
    start, end = at["stamp"], at["tasted"]
    x, y = round((cv.width - STAMP_W) / 2, 2), STAMP_Y
    mid = y + STAMP_H / 2
    g = cv.group(
        shot.front,
        cv.uid("g"),
        start=start,
        end=end,
        rotation=-2.5,
        x=cv.width / 2,
        y=mid,
        anchorX=cv.width / 2,
        anchorY=mid,
    )
    pop = [(start, 1.25), (start + 0.12, 1.0)]
    cv.keys(g, "scaleX", pop, hold=False)
    cv.keys(g, "scaleY", pop, hold=False)
    cv.rect(g, x, y, STAMP_W, STAMP_H, PAPER, CORAL, 8.0, radius=14.0)
    for words, top in zip(STAMP[:2], (y + 12, y + 74), strict=True):
        cv.text(g, cv.uid("mind-stamp"), words, x, top, round(STAMP_W), 66, STAMP_SIZE, color=INK, wrap="none")
    cv.text(g, cv.uid("mind-stamp"), STAMP[2], x, y + 140, round(STAMP_W), 44, CITE_SIZE, color=CITE_INK, wrap="none")


def _named(shot, at: dict[str, float]) -> None:
    """The name, small, over the last hold: a signature, after the laugh. The punch-in scales the shot's layers, so
    it is drawn where and at the size that land on the caption's line once the punch has happened."""
    cv = shot.cv
    a = at["named"]
    if not (shot.app.start <= a < shot.app.end):
        return
    g = cv.group(shot.front, cv.uid("g"), start=a, end=shot.app.end)
    size = mind_kit.CAPTION_SIZE / PUNCH
    pad = mind_kit.CAPTION_PAD / PUNCH
    wide = shot.measure(NAME, size=size) + 2 * pad + 12
    high = size * mind_kit.CAPTION_LEADING + pad
    x = round(cv.width / 2 - wide / 2, 2)
    y = round(PIVOT[1] + (mind_kit.CAPTION_TOP - PIVOT[1]) / PUNCH, 2)
    cv.rect(g, x, y, wide, high, INK, radius=mind_kit.CAPTION_RADIUS / PUNCH)
    cv.text(g, cv.uid("mind-name"), NAME, 0, y, cv.width, round(high), size, color=PAPER, wrap="none")


def _counter(shot) -> None:
    """The counter and the glass case in it, over any arm that has sunk behind it."""
    toon_house.ledge(shot.cv, shot.front, "parlour", MARKS_IN)
    toon_parlour.case(shot.cv, shot.front)


def dress(shot) -> None:
    """Every shot's set and props: the parlour from behind the counter on the goat, from in front of it on the fox."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    if app.who == "goat":
        toon_parlour.parlour_front(cv, mind_kit.far(cv, shot.back), app.start, app.end, _traffic(app, at))
        _contact(cv, shot.light)
        if app.start < at["swap"]:
            _stand(shot)
            _counter(shot)
        else:
            _goat_arm(shot, at)
            _counter(shot)
            _sneak(shot, at)
            if app.start <= at["stamp"] < app.end:
                _stamp(shot, at)
            _named(shot, at)
    else:
        toon_parlour.parlour_back(cv, mind_kit.far(cv, shot.back))
        _contact(cv, shot.light)
        _fox_arm(shot, at)
        _counter(shot)


def foam(cv, app, beats, face) -> None:
    """Toothpaste foam at his mouth from the taste on, in the face's own group, so it stays there when he talks."""
    start = max(app.start, sketch.events(beats, "tasted")[0][0] - 0.5)
    if start >= app.end:
        return
    mx, my = toon_rigs.rig_of("toon-goat", VERSIONS).look.mouth
    bubbles = cv.group(face, cv.uid("g"), start=start, end=app.end)

    def blob(dx: float, dy: float, r: float, fill: str) -> None:
        x, y = mx + dx, my + dy
        cv.ellipse(bubbles, toon.fx(x - r), toon.fy(y - r), toon.fh(2 * r), toon.fh(2 * r), fill)

    for dx, dy, r in BUBBLES:  # the ink first and the foam over all of it, so the bubbles read as one froth
        blob(dx, dy, r + 2.5, cv.ink)
    for dx, dy, r in BUBBLES:
        blob(dx, dy, r, FOAM)
    for dx, dy, r in BUBBLES[1::3]:
        blob(dx, dy, r * 0.35, FOAM_BLUE)


def lens(shot, setup) -> None:
    """A slow push on the goat while the reason is being built, a punch on the last line, and the street moves."""
    ev = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    if shot.app.who != "goat":
        return
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start <= ev["turn"] < shot.app.end:
        camera.push_in(shot.cv, setup, scale=[(ev["turn"], 1.0), (ev["years"], PUSH)])
    if shot.app.start <= ev["last"] < shot.app.end:
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (ev["last"], PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A whoosh on each swap, the stamp's thud and the sting on the name."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = {name: sketch.events(beats, name)[0][0] for name in EVENTS}
    swaps = [at["swap"] + 0.1, at["sneak"]]
    whoosh = synth.write_whoosh(audio / "swap.wav", swaps, end, seed=seed)
    thud = synth.write_bursts(audio / "stamp.wav", [at["stamp"]], end, THUD, seed=seed)
    sting = mind_kit.write_sting(audio / "sting.wav", [at["named"]], end)
    return [
        sketch.effect("swap", 0.0, -8.0, root, whoosh),
        sketch.effect("stamp", 0.0, -6.0, root, thud),
        sketch.effect("sting", 0.0, -9.0, root, sting),
    ]


THUMBNAIL = Thumbnail("Why\ntoothpaste?", 10.4, "He ordered vanilla", place="bottom")
POST = InstagramPost(
    title="He ordered vanilla. He will now explain the toothpaste.",
    description=(
        "Choice blindness: swap a simple choice and people will often explain it as their own. In one study of photo "
        "choices, only 13% of swaps were spotted at the time. Simple choices, in experiments; the ice cream is ours.\n"
        f"Source: {SOURCE}"
    ),
    credit="Voices: ElevenLabs premade voices Bella, George and Callum. Original characters, drawn in code.",
    hashtags=("#psychology", "#choiceblindness", "#howpeoplethink", "#icecream"),
    thumbnail=THUMBNAIL,
)
