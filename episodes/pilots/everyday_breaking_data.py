"""Everyday Breaking — a pilot of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. Vera Stillman reports, with full gravity, that a local man says he is five
minutes away for the third time. Gus Bellows cannot let it go, and knows a little too much about the man. The live
update escalates, Gus says the man takes the bus, and Vera lowers her glasses. His phone buzzes. The insert shows
whose messages these are, Gus sends "Five minutes away", and the reel cuts back to its first frame with the banner one
time worse, so the first line means something else on the replay.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events and every word the reel
shows against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import news_kit, scripting, sketch
from srstudio.news_kit import Act, Bubble, Pose
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3111
SLUG = "everyday-breaking"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Everyday Breaking — News Compiler"
DESCRIPTION = (
    "A pilot of a two-anchor parody news show: an everyday excuse reported as breaking local news, until the co-host "
    "turns out to know the man rather well."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Vera, older "
    "with a silver bob and half-moon glasses, reports that a local man says he is five minutes away for the third "
    "time. Gus, with red curls and a tangerine jacket, loses his composure, and gets oddly specific: the man is in the "
    "shower, the man takes the bus. Vera lowers her glasses and asks how he knows. His phone buzzes. The screen shows "
    "the same excuses sent from his phone. He types five minutes away, and the banner returns reading the fourth time."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
THIRD = "LOCAL MAN SAYS 'FIVE MINUTES AWAY' FOR THE THIRD TIME"
FOURTH = "LOCAL MAN SAYS 'FIVE MINUTES AWAY' FOR THE FOURTH TIME"
TICKER = ("TRAFFIC: NONE", "KEYS: ALLEGEDLY FOUND", "SHOES: ON ONE FOOT", "WEATHER: BLAMED")
LOWERS = (  # the beat it arrives on, its kicker, its one line
    (0, "LIVE", THIRD),
    (2, "THE TIMELINE", "FIRST SIGHTING OF 'FIVE MINUTES': 7:15"),
    (3, "GUS BELLOWS, CO-HOST", "CANNOT LET THIS GO"),
    (5, "LIVE UPDATE", "SUSPECT NOW 'JUST PARKING'"),
    (6, "GUS BELLOWS, CO-HOST", "OWN SOURCES CONFIRM: THE BUS"),
    (7, "VERA STILLMAN, ANCHOR", "HAS LOWERED HER GLASSES"),
)
CHAT = "Dinner, 7:30"
MESSAGES = (
    Bubble("7:15", "five minutes away"),
    Bubble("7:40", "five minutes away"),
    Bubble("8:02", "five minutes away"),
    Bubble("8:20", "just parking"),
    Bubble("8:21", "you take the bus", out=False),
)
END = 25.0

LINES = (
    Line("vera", "A local man says he's five minutes away, for the third time."),
    Line("gus", "Five minutes is a promise!"),
    Line("vera", "He first said it at seven fifteen."),
    Line("gus", "Nobody's five minutes away for an hour! He's still in the shower!"),
    Line("vera", "A live update. He now says he's just parking."),
    Line("gus", "Parking what? He takes the bus!"),
    Line("vera", "How would you know that, Gus?"),
    Line("gus", "Five minutes away."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
TYPING = Pose(eyes="down", arms="phone", mouth="flat")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, TYPING)),
    (say(3.6, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(5.0, "vera", 2, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "up"))),
    (
        first(7.1, "desk", 3, "Nobody's five minutes away for an hour!", *PLACEHOLDER),
        Act(Pose("side", "flat"), Pose("wide", "talk", "up", -4.0)),
    ),
    (
        part(8.9, "desk", 3, 7, "He's still in the shower!", *PLACEHOLDER),
        Act(Pose("side", "flat"), Pose("side", "talk", "point", 5.0)),
    ),
    (say(10.4, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "frown", "phone"))),
    (say(13.8, "desk", 5, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (hold(15.8, "vera", "", *PLACEHOLDER, "stare"), Act(Pose("over", "flat", head=3.0), Pose("wide", "flat", "phone"))),
    (say(17.3, "vera", 6, *PLACEHOLDER), Act(Pose("over", "talk", head=3.0), Pose("wide", "flat", "phone"))),
    (hold(19.2, "phone", "", *PLACEHOLDER, "buzz"), Act(Pose("over", "flat"), Pose("down", "flat", "phone"))),
    (say(21.0, "phone", 7, *PLACEHOLDER), Act(Pose("over", "flat"), Pose("down", "flat", "phone"))),
    (hold(23.2, "vera", "", *PLACEHOLDER, "fourth"), Act(Pose("over", "flat"), TYPING)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("first", "stare", "buzz", "fourth")
POST = InstagramPost(
    title="Who do you know who is always five minutes away?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#runninglate", "#fiveminutesaway", "#everydaylife"),
    thumbnail=Thumbnail(
        "Five minutes away.\nThird time.", 9.5, "News Compiler", focus=(540.0, 400.0), zoom=1.15, place="top"
    ),
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, its events happen once and in order, the first picture speaks, the acts match the
    beats, and no word the reel shows is one the show keeps off it."""
    sketch.check(sk)
    if len(ACTS) != len(sk.beats):
        raise sketch.SketchError(f"{len(ACTS)} acts for {len(sk.beats)} beats")
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the anchor's line")
    words = (
        *(q.text for q in sk.lines),
        *TICKER,
        *(w for row in LOWERS for w in row[1:]),
        FOURTH,
        *(m.text for m in MESSAGES),
        POST.title,
        POST.description,
    )
    for text in words:
        news_kit.check_copy(text)


def overlay(cv, parent, beats, end, measure) -> None:
    """Everything over the picture: the PARODY tag from frame 1, the banner and ticker off during the phone, the
    headline back one time worse."""
    news_kit.sign(cv, parent)
    buzz = sketch.events(beats, "buzz")[0][0]
    fourth = sketch.events(beats, "fourth")[0][0]
    sends = beats[[b.line for b in beats].index(7)].start
    news_kit.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_kit.banner(cv, parent, 0.0, buzz, measure)
    news_kit.banner(cv, parent, fourth, end, measure, id="news-banner-last", slide=False)
    starts = [beats[index].start for index, _, _ in LOWERS]
    for a, b, (_, kicker, line) in zip(starts, [*starts[1:], buzz], LOWERS, strict=True):
        news_kit.lower_third(cv, parent, kicker, line, a, b, measure)
    news_kit.lower_third(cv, parent, "LIVE", FOURTH, fourth, end, measure, slide=False)
    news_kit.phone_insert(
        cv, parent, CHAT, (*MESSAGES, Bubble("8:23", "five minutes away", at=sends + 0.9)), buzz, fourth, measure
    )
    news_kit.bug(cv, parent, 0.0, end, measure)
    news_kit.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening and on the cut back, the buzz on the reveal, the tick of the message sent."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    buzz = sketch.events(beats, "buzz")[0][0]
    fourth = sketch.events(beats, "fourth")[0][0]
    sends = beats[[b.line for b in beats].index(7)].start
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, fourth], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    phone = synth.write_buzz(audio / "buzz.wav", [buzz], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [sends + 0.9], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("buzz", 0.0, -4.0, root, phone),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
