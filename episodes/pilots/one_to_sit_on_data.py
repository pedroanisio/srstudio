"""One to Sit On — a real roast of News Compiler, main trigger "folding phone, or folded phone?": the sketch as data.

Apple's first folding iPhone, the iPhone Duo, sold out within hours; it costs $1,999, some deliveries are expected in
2027, and on 2 November 2026 Apple said it is hard to predict when supply and demand will be in balance. Vera reads it
flat. Gus's own phone already folds, he orders a pair, he will have the money by 2027, and his bank says
the same thing Apple does. Vera asks why a pair. One to sit on. Every fact traces to
``pilots/news/one-to-sit-on/sources.md``; Gus's phone, his pair and his bank are the show's.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :data:`STORY` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import Story

from srstudio import foley as synth
from srstudio import news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 4103
SLUG = "one-to-sit-on"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "One to Sit On — News Compiler"
STORY_DATE = "2026-11-02"
RIG = 6  # the anchors' version: hands v6, the pair (ADR 0103)
SOURCE = Source(
    "TechCrunch", "Nov 2, 2026", "Apple says it’s ‘hard to predict’ when iPhone Duo constraints will improve"
)
ALSO = "The Verge, Nov 2, 2026: Apple is ‘not able to predict’ when it’ll have enough iPhone Duos to go around"
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports that Apple's first folding iPhone sold "
    "out in hours and that Apple cannot predict when supply will meet demand, and her co-host, whose own phone already "
    "folds, orders a pair."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads from a source card: Apple's first folding iPhone sold out in hours. Gus, with brown curls and an "
    "orange jacket, holds up his phone: his already folds. Vera says it costs 1,999 dollars. Gus says he "
    "will take a pair. Vera says some will not arrive until 2027. Gus says perfect, he will have the money by then. "
    "Vera says Apple cannot predict when supply and demand will be in balance; Gus says his bank says the "
    "same thing. Vera lowers her glasses and asks why a pair. Gus pauses: one to sit on."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "APPLE'S FIRST FOLDING IPHONE, THE IPHONE DUO, SOLD OUT WITHIN HOURS",
    "APPLE: 'HARD TO PREDICT' WHEN SUPPLY AND DEMAND WILL BE IN BALANCE",
    "SOME IPHONE DUO DELIVERIES EXPECTED IN 2027",
)
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # a name only while that anchor speaks or fills the shot; the show's own kicker across a volley
    (2, STILL_LIVE, "IPHONE DUO: $1,999, SOLD OUT"),
    (3, GUS_NAME, "ORDERING A PAIR"),
    (4, STILL_LIVE, "SOME DELIVERIES IN 2027"),
    (5, GUS_NAME, "BUDGETING BY BACKORDER"),
    (6, STILL_LIVE, "SUPPLY VS DEMAND: NOT ABLE TO PREDICT"),
    (7, GUS_NAME, "ALSO CONSTRAINED"),
    (8, STILL_LIVE, "FIRST FOLDING IPHONE: SOLD OUT"),
)
END = 24.0

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Apple's first folding iPhone sold out in hours."),
    Line("gus", "Folding? Mine already folds."),
    Line("vera", "It costs 1,999 dollars."),
    Line("gus", "I'll take a pair."),
    Line("vera", "Some won't arrive until 2027."),
    Line("gus", "Perfect. I'll have the money by then."),
    Line("vera", "Apple can't predict when supply and demand will be in balance."),
    Line("gus", "My bank says the same thing."),
    Line("vera", "Why a pair, Gus?"),
    Line("gus", "One to sit on."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold = script.say, script.hold
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="side", mouth="flat", arms="chest")
LOW = Pose("over", "flat", head=3.0)  # the glasses down, the stare
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "card"), Act(READ, Pose("level", "flat", head=-2.0))),
    (say(2.8, "gus", 1, *PLACEHOLDER, "folded"), Act(STILL, Pose("squint", "talk", "phone", -4.0))),
    (say(5.0, "vera", 2, *PLACEHOLDER), Act(READ, Pose("wide", "flat", "chest"))),
    (say(6.8, "gus", 3, *PLACEHOLDER, "pair"), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(8.0, "vera", 4, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(10.0, "gus", 5, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "up", -3.0))),
    (say(12.2, "vera", 6, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(15.6, "gus", 7, *PLACEHOLDER, "bank"), Act(STILL, Pose("squint", "talk", "chest", 4.0))),
    (say(18.2, "vera", 8, *PLACEHOLDER, "stare"), Act(Pose("over", "talk", head=3.0), Pose("side", "flat", "chest"))),
    (hold(19.8, "gus", "", *PLACEHOLDER, "beat"), Act(LOW, Pose("down", "flat", "phone", -3.0))),
    (say(21.2, "gus", 9, *PLACEHOLDER, "end"), Act(LOW, Pose("level", "grin", "phone", 4.0))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "folded", "pair", "bank", "stare", "beat", "end")
POST = InstagramPost(
    title="Folding phone, or folded phone?",
    description=f"{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}\n{ALSO}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#iphoneduo", "#apple", "#foldablephone", "#technews"),
    thumbnail=Thumbnail("Sold out\nin hours.", 5.6, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST, parody=True)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks."""
    STORY.validate(sk)


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words over the desk: nothing fills the frame, so the anchors carry every beat."""
    STORY.overlay(cv, parent, beats, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and after the last word, a whoosh on the card, a tick as Gus orders the pair, his phone
    buzzing as his bank agrees. Nothing
    under Gus's pause: the room goes quiet before "One to sit on."."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    pair = sketch.events(beats, "pair")[0][0]
    last = sketch.events(beats, "end")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, last + 0.9], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [pair], end)
    bank = sketch.events(beats, "bank")[0][0]
    said = min(b for a, b in speech if a >= bank - 0.05)  # the bank line's end: his phone buzzes, the bank agreeing
    buzz = synth.write_buzz(audio / "buzz.wav", [said + 0.1], end, seed=seed)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
        sketch.effect("buzz", 0.0, -10.0, root, buzz),
    ]
