"""Seabird Jet Lag — a real roast of News Compiler, main trigger "wait, did you see this?": the sketch as data.

A study in Science, 29 October 2026: Manx shearwaters flying fast across longitudes outrun their body clocks, so their
sun compass points them off course, and they fly on by it even with land in sight. Vera reads it flat. Gus hears a man
who will not ask for directions and takes the birds' side. The map on his phone shows the veer while Vera says it, and
comes back with his wife's pin at home and his own dot out at sea. He ends the reel by asking the way. Every fact
traces to ``pilots/news/seabird-jet-lag/sources.md``; his wife and his dot are the show's.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :data:`STORY` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import Story

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_inked import Pin
from srstudio.news_kit import Act, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3120
SLUG = "seabird-jet-lag"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Seabird Jet Lag — News Compiler"
STORY_DATE = "2026-10-29"
SOURCE = Source("Science News", "Oct 29, 2026", "Seabirds get jet lag, too — and it can throw them a bit off course")
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports that seabirds get jet lag and fly off "
    "course, and her co-host defends them for never asking directions, until his wife walks home."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads from a source card: seabirds get jet lag. Gus, with red curls and a tangerine jacket, asks what "
    "airline. A phone map shows a bird drifting off a dashed line to home. Gus says fifteen degrees is nothing and "
    "shouts never ask for directions. Vera tells him his wife called: she got out and walked, and she is home. The map "
    "returns with her pin at home and Gus's dot wandering out at sea. Close on Gus, who quietly asks which way that is."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "MANX SHEARWATERS STUDIED: 1,045",
    "GPS TRACKING: 20 YEARS, 3,688 TRIPS",
    "SOURCE: LEWIN ET AL., SCIENCE, OCT 29",
)
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
SIDE = "TAKING THE BIRDS' SIDE"
LOWERS = (  # a name only while that anchor speaks or fills the shot
    (2, "THE STUDY", "CLOCKS CAN LAG UP TO AN HOUR"),
    (4, GUS_NAME, SIDE),
    (5, VERA_NAME, "LAND: VISIBLE"),
    (6, GUS_NAME, SIDE),
    (7, VERA_NAME, "A FEW KILOMETERS OFF"),
    (8, GUS_NAME, "CALLS THIS A WIN"),
    (9, STILL_LIVE, "WIFE HAS CALLED THE NEWSROOM"),
    (14, GUS_NAME, "FIRST RECORDED REQUEST FOR DIRECTIONS"),
)
VEER_TITLE, LOST_TITLE = "The Way Home", "Where's Gus"
HOME = (560.0, 150.0)
VEER = (  # to scale: 15 degrees off the dashed line, then the correction along the coast
    (60.0, 560.0),
    (240.0, 479.0),
    (440.0, 388.0),
    (640.0, 298.0),
    (610.0, 220.0),
    HOME,
)
VEER_PINS = (Pin(*HOME, "HOME", news_kit.MINT), Pin(420.0, 397.0, "UP TO 15° OFF", news_kit.BUTTER, below=True))
WANDER = ((430.0, 420.0), (320.0, 520.0), (420.0, 610.0), (300.0, 620.0), (250.0, 360.0), (110.0, 520.0))
LOST_PINS = (
    Pin(*HOME, "WIFE: HOME", news_kit.MINT),
    Pin(110.0, 520.0, "GUS: NOT LOST", news_kit.TANGERINE, below=True),
)
END = 26.3

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Seabirds get jet lag."),
    Line("gus", "What airline?"),
    Line("vera", "Their clocks can lag up to an hour, so they veer up to fifteen degrees."),
    Line("gus", "Fifteen degrees? That's nothing!"),
    Line("vera", "Even with land in sight, they stick with the compass."),
    Line("gus", "Never ask! Never ask for directions!"),
    Line("vera", "It adds a few kilometers. They still get home."),
    Line("gus", "See? Never ask!"),
    Line("vera", "Gus, your wife called. She got out and walked. She's home."),
    Line("gus", "Which way is that?"),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="side", mouth="flat", arms="chest")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "card"), Act(READ, Pose(eyes="level", mouth="flat"))),
    (say(1.55, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "up", -4.0))),
    (first(2.6, "vera", 2, "Their clocks can lag up to an hour,", *PLACEHOLDER), Act(READ, LISTEN)),
    (part(4.9, "phone", 2, 8, "so they veer up to fifteen degrees.", *PLACEHOLDER, "veer"), Act(STILL, LISTEN)),
    (say(6.6, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(8.75, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "grin", "chest"))),
    (say(11.6, "desk", 5, *PLACEHOLDER), Act(Pose("side", "flat"), Pose("wide", "talk", "point", 5.0))),
    (say(13.8, "vera", 6, *PLACEHOLDER), Act(READ, Pose("side", "grin", "point"))),
    (say(16.5, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("level", "grin", "up", -4.0))),
    (
        first(18.0, "desk", 8, "Gus, your wife called.", *PLACEHOLDER),
        Act(Pose("over", "talk", head=3.0), Pose("wide", "flat", "rest")),
    ),
    (
        part(19.3, "phone", 8, 4, "She got out and walked.", *PLACEHOLDER, "wife"),
        Act(Pose("over", "talk", head=3.0), Pose("wide", "flat", "rest")),
    ),
    (part(20.7, "phone", 8, 9, "She's home.", *PLACEHOLDER), Act(Pose("over", "flat"), Pose("wide", "flat", "rest"))),
    (hold(21.4, "phone", "", *PLACEHOLDER, "lost"), Act(Pose("over", "flat"), Pose("down", "flat", "phone"))),
    (say(23.7, "gus", 9, *PLACEHOLDER), Act(Pose("over", "flat"), Pose("down", "talk", "phone", 3.0))),
    (hold(24.8, "gus", "", *PLACEHOLDER, "asked"), Act(Pose("over", "flat"), Pose("level", "flat", "phone"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "veer", "wife", "lost", "asked")
POST = InstagramPost(
    title="Would a seabird stop and ask?",
    description=f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#seabirds", "#jetlag", "#science", "#sciencenews"),
    thumbnail=Thumbnail("Seabirds\nget jet lag.", 7.5, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks, the words on the two maps among them."""
    STORY.validate(sk, (VEER_TITLE, LOST_TITLE, *(pin.label for pin in (*VEER_PINS, *LOST_PINS))))


def maps(beats) -> tuple[tuple[float, float], tuple[float, float]]:
    """When each map is up: the veer through its half of the line, the second one until Gus asks."""
    veer = sketch.events(beats, "veer")[0][0]
    wife = sketch.events(beats, "wife")[0][0]
    return (veer, next(b.start for b in beats if b.start > veer)), (wife, next(b.start for b in beats if b.line == 9))


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words, and the two maps over them."""
    veer, lost = maps(beats)

    def phone() -> None:
        news_inked.route_insert(
            cv,
            parent,
            VEER_TITLE,
            VEER,
            VEER_PINS,
            *veer,
            measure,
            direct=(VEER[0], HOME),
            draw=(veer[1] - veer[0]) * 0.8,
            id="news-veer",
        )
        news_inked.route_insert(
            cv,
            parent,
            LOST_TITLE,
            WANDER,
            LOST_PINS,
            *lost,
            measure,
            marker="dot",
            draw=(lost[1] - lost[0]) * 0.9,
            id="news-lost",
        )

    STORY.overlay(cv, parent, beats, end, measure, (veer, lost), phone)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and the last word, a whoosh on the card and each map, a tick on her pin."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    veer, lost = maps(beats)
    asked = sketch.events(beats, "asked")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, asked + 0.05], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05, veer[0], lost[0]], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [lost[0] + 1.2], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
