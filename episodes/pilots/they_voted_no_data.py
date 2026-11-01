"""They Voted No — a real roast of News Compiler, main trigger "wait, did you see this?": the sketch as data.

Alberta stopped changing its clocks on 1 November 2026. In 2021 Albertans voted on year-round daylight time and it lost,
50.2 to 49.8, and it started anyway. Vera reads that flat. Gus hears only that his oven, an hour off every winter and
never touched, is right at last. Every fact traces to ``pilots/news/they-voted-no/sources.md``; the oven is the show's.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :data:`STORY` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import Story

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3141
SLUG = "they-voted-no"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "They Voted No — News Compiler"
STORY_DATE = "2026-11-01"
SOURCE = Source("Red Deer Advocate", "Oct 30, 2026", "Reminder! Don't set clocks back in Alberta")
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports that Alberta stopped changing its "
    "clocks after a referendum on it lost, and her co-host thanks the province for fixing his oven."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads from a source card: Alberta has stopped changing its clocks. She says the 2021 vote lost, fifty "
    "point two to forty-nine point eight. Gus, with red curls and a tangerine jacket, says his oven is an hour off "
    "every winter. A plain stove fills the screen, its clock tagged one hour off. The digits do not change, and the "
    "tag turns to correct. Gus weeps and thanks the people of Alberta. Vera lowers her glasses: they voted no."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "ALBERTA TIME: NO MORE CLOCK CHANGES FROM NOV. 1",
    "2021 REFERENDUM: FAILED, 50.2% TO 49.8%",
    "PREMIER: CLOCK CHANGES COULD RETURN IF IT PROVES UNPOPULAR",
)
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
OVEN, TIME, WRONG, RIGHT = "GUS'S OVEN", "7:42", "1 HOUR OFF", "CORRECT"
LOWERS = (  # a name only while that anchor fills the shot; the show's own kicker across a volley
    (3, STILL_LIVE, "2021: NO 50.2, YES 49.8"),
    (6, GUS_NAME, "STILL CHECKING"),
    (7, STILL_LIVE, "OLDER DEVICES MAY NEED SETTING BY HAND"),
    (8, GUS_NAME, "OVEN OWNER"),
    (12, STILL_LIVE, "ALBERTA TIME: YEAR-ROUND"),
    (14, GUS_NAME, "GRATEFUL TO ALBERTA"),
    (15, VERA_NAME, "STILL REPORTING"),
)
END = 30.4

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Alberta has stopped changing its clocks."),
    Line("gus", "They can do that?"),
    Line("vera", "In 2021 Albertans voted on it."),
    Line("vera", "It lost, fifty point two to forty-nine point eight."),
    Line("gus", "So it lost."),
    Line("vera", "It started Sunday."),
    Line("gus", "Did anyone tell Alberta?"),
    Line("vera", "Older devices may be an hour off, and need setting by hand."),
    Line("gus", "My oven's an hour off every winter. I never touch it."),
    Line("vera", "In Alberta, your oven is now right."),
    Line("gus", "All year?"),
    Line("vera", "Permanently."),
    Line("gus", "The people of Alberta did this for me."),
    Line("vera", "They voted no."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="side", mouth="flat", arms="chest")
LOW = Pose("over", "flat", head=3.0)  # the glasses down, the stare
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "card"), Act(READ, Pose("level", "flat", head=-2.0))),
    (say(2.3, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(3.3, "vera", 2, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(5.5, "vera", 3, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(8.9, "gus", 4, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", -3.0))),
    (say(10.0, "vera", 5, *PLACEHOLDER), Act(READ, Pose("wide", "flat", "chest"))),
    (say(11.5, "gus", 6, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", 4.0))),
    (say(13.1, "desk", 7, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(16.6, "gus", 8, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", -4.0))),
    (hold(19.4, "phone", "", *PLACEHOLDER, "oven"), Act(STILL, LISTEN)),
    (first(20.7, "phone", 9, "In Alberta, your oven is now", *PLACEHOLDER), Act(READ, LISTEN)),
    (part(22.3, "phone", 9, 6, "right.", *PLACEHOLDER, "right"), Act(READ, LISTEN)),
    (say(23.1, "gus", 10, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -4.0))),
    (say(23.9, "vera", 11, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(25.0, "gus", 12, *PLACEHOLDER), Act(STILL, Pose("weep", "talk", "chest", 3.0))),
    (hold(26.85, "vera", "", *PLACEHOLDER, "stare"), Act(LOW, Pose("weep", "flat", "chest"))),
    (say(28.2, "vera", 13, *PLACEHOLDER, "no"), Act(Pose("over", "talk"), Pose("weep", "flat", "chest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "oven", "right", "stare", "no")
POST = InstagramPost(
    title="Did anyone tell Alberta?",
    description=f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#alberta", "#daylightsaving", "#parodynews", "#canada"),
    thumbnail=Thumbnail("My oven was right.", 22.5, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks, the words on the oven among them."""
    STORY.validate(sk, (OVEN, WRONG, RIGHT))


def oven_span(beats) -> tuple[float, float]:
    """When the stove is up: from the held look at the clock to Gus's next line."""
    right = sketch.events(beats, "right")[0][0]
    return sketch.events(beats, "oven")[0][0], next(b.start for b in beats if b.start > right)


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words, and the stove over them."""
    span = oven_span(beats)
    right = sketch.events(beats, "right")[0][0]

    def stove() -> None:
        news_inked.oven_clock(cv, parent, OVEN, TIME, WRONG, RIGHT, *span, measure, right_at=right)

    STORY.overlay(cv, parent, beats, end, measure, (span,), stove)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and after the last word, a whoosh on the card and the stove, a tick on the tag. Nothing
    under the stare: the room goes quiet before "They voted no."."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    start, _ = oven_span(beats)
    right = sketch.events(beats, "right")[0][0]
    no = sketch.events(beats, "no")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, no + 1.1], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05, start], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [right], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
