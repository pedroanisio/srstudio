"""Different Reasons — a real roast of News Compiler, main trigger "remember your driving test?": the sketch as data.

Kimi Antonelli became Formula One world champion in Mexico City on 1 November 2026, at 20 years and 68 days, the
youngest ever. He needed ninth place and came third. Vera reads the record flat. Gus hears one number: at 20 he failed
his driving test, and at 23, Sebastian Vettel's age when he set the old record, he failed it again. Antonelli's father
did not want him to become a driver. Neither did Gus's, for different reasons. Every fact traces to
``pilots/news/different-reasons/sources.md``; Gus's tests and his father are the show's.

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

SEED = 3143
SLUG = "different-reasons"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Different Reasons — News Compiler"
STORY_DATE = "2026-11-01"
RIG = 6  # the anchors' version: hands v6, the pair (ADR 0103)
SOURCE = Source("AFP", "Nov 1, 2026", "Fast and funny, Antonelli becomes Formula One's youngest king")
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports that a 20-year-old is the youngest "
    "Formula One world champion ever, and her co-host remembers failing his driving test at that age, and again at "
    "the age of the old record."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads from a source card: a 20-year-old is Formula One world champion, at 20 years and 68 days the "
    "youngest ever. Gus, with brown curls and an orange jacket, throws up his hands and says that at 20 he failed his "
    "driving test. Vera says the champion only needed ninth place and came third; Gus calls him a show-off. The old "
    "record was Vettel's, at 23; Gus failed his test again at 23. Vera says the champion's father did not want him to "
    "be a driver. Gus says his did not either. Vera lowers her glasses. Gus: different reasons."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "KIMI ANTONELLI, 20, CROWNED F1 WORLD CHAMPION IN MEXICO CITY",
    "FIRST ITALIAN CHAMPION SINCE ALBERTO ASCARI IN 1953",
    "TITLE SEALED WITH FOUR RACES STILL TO RUN",
)
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # a name only while that anchor speaks or fills the shot; the show's own kicker across a volley
    (2, STILL_LIVE, "YOUNGEST F1 CHAMPION EVER"),
    (3, GUS_NAME, "FAILED DRIVING TEST AT 20"),
    (4, STILL_LIVE, "NEEDED: 9TH. FINISHED: 3RD."),
    (8, STILL_LIVE, "OLD RECORD: VETTEL, AGE 23"),
    (9, GUS_NAME, "FAILED AGAIN AT 23"),
    (10, STILL_LIVE, "HIS DAD DIDN'T WANT HIM RACING"),
)
END = 25.6

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "A 20-year-old is Formula One world champion."),
    Line("gus", "Twenty?"),
    Line("vera", "20 years and 68 days. The youngest ever."),
    Line("gus", "At 20, I failed my driving test."),
    Line("vera", "He only needed to finish ninth."),
    Line("gus", "And?"),
    Line("vera", "He came third."),
    Line("gus", "Show-off."),
    Line("vera", "The old record was Vettel's, at 23."),
    Line("gus", "At 23, I failed it again."),
    Line("vera", "His father didn't want him to be a driver."),
    Line("gus", "Mine neither."),
    Line("gus", "Different reasons."),
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
    (say(3.0, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(3.8, "vera", 2, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(6.8, "gus", 3, *PLACEHOLDER, "test"), Act(STILL, Pose("down", "talk", "chest", 4.0))),
    (say(9.1, "vera", 4, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(11.2, "gus", 5, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", -3.0))),
    (say(11.9, "vera", 6, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (say(13.1, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 5.0))),
    (say(14.1, "vera", 8, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(16.5, "gus", 9, *PLACEHOLDER, "again"), Act(STILL, Pose("wide", "talk", "point", -4.0))),
    (say(18.4, "vera", 10, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(21.0, "desk", 11, *PLACEHOLDER), Act(Pose(eyes="side", mouth="flat"), Pose("level", "talk", "chest", 3.0))),
    (hold(22.2, "vera", "", *PLACEHOLDER, "stare"), Act(LOW, Pose("side", "grin", "chest"))),
    (say(23.7, "gus", 12, *PLACEHOLDER, "end"), Act(LOW, Pose("down", "talk", "chest", -3.0))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "test", "again", "stare", "end")
POST = InstagramPost(
    title="Remember your driving test?",
    description=(
        f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}\n"
        "RTÉ Sport, Nov 2, 2026: History made as Kimi Antonelli crowned F1 world champion"
    ),
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#formula1", "#f1", "#drivingtest", "#parodynews"),
    thumbnail=Thumbnail(
        "At 20, I failed\nmy driving test.", 7.6, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"
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
    """The sting on the opening and after the last word, a whoosh on the card, a tick on each failed test. Nothing
    under the stare: the room goes quiet before "Different reasons."."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    tests = [sketch.events(beats, name)[0][0] for name in ("test", "again")]
    last = sketch.events(beats, "end")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, last + 0.9], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", tests, end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
