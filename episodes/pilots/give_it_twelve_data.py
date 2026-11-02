"""Give It Twelve — a real roast of News Compiler, main trigger "wait, did you see this?": the sketch as data.

Karl Bushby set off from South America in 1998 to walk home to Hull with no transport, and on 2 November 2026 he
arrives. The walk was meant to take twelve years. Vera reads the feat flat. Gus hears one thing: an estimate that came
in at twenty-eight, which is his builder, who will not come out when it drizzles. The man swam the English Channel.
Asked what comes next, he does not know yet, and Gus gives it twelve years. Every fact traces to
``pilots/news/give-it-twelve/sources.md``; the builder and the kitchen are the show's.

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

SEED = 3142
SLUG = "give-it-twelve"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Give It Twelve — News Compiler"
STORY_DATE = "2026-11-02"
RIG = 6  # the anchors' version: hands v6, the pair (ADR 0103)
SOURCE = Source(
    "AFP", "Nov 2, 2026", "UK adventurer ends epic 28-year journey across jungles, mountains and a frozen sea"
)
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports that a man has walked home to Hull "
    "from Chile, twenty-eight years after setting off on a walk meant to take twelve, and her co-host recognises his "
    "builder."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads from a source card: a man has walked home to Hull from Chile, fifty thousand kilometers with no "
    "transport. Gus, with red curls and a tangerine jacket, asks if not even a bus. Vera says he set off in 1998 on a "
    "walk meant to take twelve years. Gus says that is his builder, who will not come out when it drizzles, while the "
    "man swam the English Channel. Vera says the man does not know what comes next. Gus says give it twelve years. "
    "Vera lowers her glasses: twenty-eight."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "KARL BUSHBY, 57, ENDS 50,000 KM WALK HOME TO HULL",
    "SET OFF FROM SOUTH AMERICA IN 1998: NO TRANSPORT",
    "CIVIC WELCOME TODAY FROM HULL'S MAYOR",
)
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # a name only while that anchor speaks or fills the shot; the show's own kicker across a volley
    (2, STILL_LIVE, "50,000 KM ON FOOT, NO TRANSPORT"),
    (5, STILL_LIVE, "PLANNED: 12 YEARS. TOOK: 28."),
    (8, GUS_NAME, "KITCHEN DUE IN 2019"),
    (9, STILL_LIVE, "SWAM THE ENGLISH CHANNEL"),
    (10, GUS_NAME, "STILL WAITING ON A BUILDER"),
    (11, STILL_LIVE, "HOMECOMING: HULL, TODAY"),
    (13, STILL_LIVE, "WHAT'S NEXT: UNDECIDED"),
)
END = 26.8

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "A man just walked home to Hull. From Chile."),
    Line("gus", "Walked?"),
    Line("vera", "50,000 kilometers. No transport at all."),
    Line("gus", "Not even a bus?"),
    Line("vera", "He set off in 1998."),
    Line("vera", "It was meant to take twelve years."),
    Line("gus", "And it took twenty-eight?"),
    Line("vera", "Twenty-eight."),
    Line("gus", "That's my builder!"),
    Line("vera", "He swam the English Channel."),
    Line("gus", "Mine won't come out if it drizzles."),
    Line("vera", "He's due home today."),
    Line("gus", "And what's next?"),
    Line("vera", "He doesn't know yet."),
    Line("gus", "Give it twelve years."),
    Line("vera", "Twenty-eight."),
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
    (say(2.6, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(3.4, "vera", 2, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(6.0, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 4.0))),
    (say(7.2, "vera", 4, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(8.8, "vera", 5, *PLACEHOLDER), Act(READ, Pose("wide", "flat", "chest"))),
    (say(10.8, "gus", 6, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest", -3.0))),
    (say(12.3, "vera", 7, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (say(13.3, "gus", 8, *PLACEHOLDER, "builder"), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(14.8, "vera", 9, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(16.6, "gus", 10, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", -4.0))),
    (say(18.6, "desk", 11, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(19.8, "gus", 12, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", -3.0))),
    (say(21.0, "vera", 13, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(22.4, "gus", 14, *PLACEHOLDER, "callback"), Act(STILL, Pose("side", "talk", "chest", 4.0))),
    (hold(23.8, "vera", "", *PLACEHOLDER, "stare"), Act(LOW, Pose("side", "grin", "chest"))),
    (say(25.2, "vera", 15, *PLACEHOLDER, "end"), Act(Pose("over", "talk"), Pose("wide", "flat", "chest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "builder", "callback", "stare", "end")
POST = InstagramPost(
    title="Sound like your builder?",
    description=f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#hull", "#walking", "#adventure", "#parodynews"),
    thumbnail=Thumbnail(
        "Twelve years,\nhe said.", 13.9, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"
    ),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST, parody=True)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks."""
    STORY.validate(sk)


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words over the desk: nothing fills the frame, so the anchors carry every beat."""
    STORY.overlay(cv, parent, beats, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and after the last word, a whoosh on the card, a tick on the builder. Nothing under
    the stare: the room goes quiet before "Twenty-eight."."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    builder = sketch.events(beats, "builder")[0][0]
    last = sketch.events(beats, "end")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, last + 0.9], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [builder], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
