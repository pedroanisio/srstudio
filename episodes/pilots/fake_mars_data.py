"""Fake Mars — a real roast of News Compiler, main trigger "wait, did you see this?": the sketch as data.

Four volunteers came out on 31 October 2026 after 378 days in NASA's 3D-printed Mars habitat in Houston. Vera reads the
hardship straight. Gus hears a rental: seventeen hundred square feet, a landlord who answers late. When she says NASA
wants volunteers for the next one he applies from the desk, stops at the psychological assessment, and gets his answer
on the phone. Every fact traces to ``pilots/news/fake-mars/sources.md``; the rent, the landlord and his application are
the show's, and no chat on screen names NASA.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :data:`STORY` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import Story

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Bubble, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3122
SLUG = "fake-mars"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Fake Mars — News Compiler"
STORY_DATE = "2026-10-31"
SOURCE = Source("Engadget", "Oct 31, 2026", "NASA's second year-long Mars simulation mission ends today")
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports that four people spent a year on fake "
    "Mars in Houston, and her co-host, hearing a rental, applies and is rejected."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reports that four people spent a year on fake Mars in Houston. Gus, with red curls and a tangerine "
    "jacket, asks if anybody told them, then asks the rent. She lists the hardships and he says that's his landlord. "
    "She says NASA wants volunteers for the next one and he starts applying on his phone. She mentions the "
    "psychological assessment. His thumbs stop. His phone shows the application's answer: no."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = ("NASA MARS SIMULATION: 378 DAYS", "HABITAT: 1,700 SQUARE FEET, 3D-PRINTED", "LOCATION: HOUSTON, TEXAS")
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # a name only while that anchor speaks or fills the shot
    (2, GUS_NAME, "CONCERNED FOR THE CREW"),
    (3, VERA_NAME, "HABITAT: 1,700 SQUARE FEET"),
    (4, GUS_NAME, "APARTMENT HUNTING"),
    (5, VERA_NAME, "378 DAYS"),
    (6, GUS_NAME, "IN A DISPUTE WITH HIS LANDLORD"),
    (7, VERA_NAME, "NEXT MISSION: NO EARLIER THAN AUGUST 2027"),
    (8, GUS_NAME, "APPLYING"),
    (9, VERA_NAME, "PHYSICAL AND PSYCHOLOGICAL ASSESSMENTS"),
    (11, GUS_NAME, "APPLICATION IN PROGRESS"),
    (13, STILL_LIVE, "APPLICATION CLOSED"),
)
CHAT = "Application"
MESSAGES = (Bubble("3:01", "Why Mars?", out=False), Bubble("3:02", "the rent"))
VERDICT = "Result: No."
END = 28.0

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Four people spent a year on fake Mars. In Houston."),
    Line("gus", "Did anybody tell them?"),
    Line("vera", "They volunteered. Seventeen hundred square feet, for four."),
    Line("gus", "Seventeen hundred? What's the rent?"),
    Line("vera", "The crew faced isolation, limited resources and delayed messages."),
    Line("gus", "That's my landlord!"),
    Line("vera", "NASA seeks volunteers for the next one."),
    Line("gus", "Applying. Applying now!"),
    Line("vera", "You must pass a psychological assessment."),
    Line("gus", "Is it multiple choice?"),
    Line("vera", "Gus has been rejected by a fake planet. In Houston."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="level", mouth="flat")
TYPING = Pose(eyes="down", arms="phone", mouth="grin")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (first(0.0, "vera", 0, "Four people spent a year on fake Mars.", *PLACEHOLDER, "card"), Act(READ, LISTEN)),
    (part(2.1, "vera", 0, 8, "In Houston.", *PLACEHOLDER), Act(READ, LISTEN)),
    (say(3.0, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest", -4.0))),
    (say(4.4, "vera", 2, *PLACEHOLDER), Act(READ, Pose("side", "flat", "chest"))),
    (say(7.6, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(9.8, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "flat", "chest"))),
    (say(13.0, "desk", 5, *PLACEHOLDER), Act(Pose("side", "flat"), Pose("wide", "talk", "point", 5.0))),
    (say(14.3, "vera", 6, *PLACEHOLDER), Act(READ, Pose("side", "grin", "chest"))),
    (say(16.8, "desk", 7, *PLACEHOLDER, "apply"), Act(Pose("side", "flat"), Pose("down", "talk", "phone", 3.0))),
    (say(18.4, "vera", 8, *PLACEHOLDER), Act(READ, TYPING)),
    (hold(20.4, "desk", "", *PLACEHOLDER, "stop"), Act(Pose("over", "flat", head=3.0), Pose("wide", "flat", "phone"))),
    (say(21.8, "gus", 9, *PLACEHOLDER), Act(Pose("over", "flat"), Pose("wide", "talk", "phone"))),
    (hold(23.0, "phone", "", *PLACEHOLDER, "result"), Act(Pose("over", "flat"), Pose("down", "flat", "phone"))),
    (
        first(25.0, "desk", 10, "Gus has been rejected by a fake planet.", *PLACEHOLDER),
        Act(Pose("over", "talk", head=3.0), Pose("down", "frown", "phone")),
    ),
    (
        part(27.0, "desk", 10, 8, "In Houston.", *PLACEHOLDER),
        Act(Pose("over", "talk", head=3.0), Pose("shut", "frown")),
    ),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "apply", "stop", "result")
POST = InstagramPost(
    title="Would you live on fake Mars for a year?",
    description=f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#nasa", "#mars", "#houston", "#space"),
    thumbnail=Thumbnail("A year on\nfake Mars.", 3.4, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks, the words in the chat among them."""
    STORY.validate(sk, (CHAT, VERDICT, *(m.text for m in MESSAGES)))


def result(beats) -> tuple[float, float]:
    """When the phone is up: from the result to Vera's last line."""
    return sketch.events(beats, "result")[0][0], next(b.start for b in beats if b.line == 10)


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words, with the application on the phone over them."""
    up, down = result(beats)

    def phone() -> None:
        chat = (*MESSAGES, Bubble("3:03", VERDICT, out=False, at=up + 1.0))
        news_inked.phone_insert(cv, parent, CHAT, chat, up, down, measure)

    STORY.overlay(cv, parent, beats, end, measure, ((up, down),), phone)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and the last line, a whoosh on the card and the phone, ticks of typing, the buzz."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    up, down = result(beats)
    apply, stop = sketch.events(beats, "apply")[0][0], sketch.events(beats, "stop")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, down], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05, up], end, seed=seed)
    typed = [apply + 0.3 * i for i in range(int((stop - apply) / 0.3))]
    tick = news_kit.write_tick(audio / "tick.wav", typed, end)
    buzz = synth.write_buzz(audio / "buzz.wav", [up + 1.0], end, seed=seed)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -14.0, root, tick),
        sketch.effect("buzz", 0.0, -10.0, root, buzz),
    ]
