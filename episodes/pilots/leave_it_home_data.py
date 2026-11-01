"""Leave It Home — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. It has not rained in nine weeks because one man keeps bringing his
umbrella. Farmers ask him to leave it at home, and he does. A cloud the size of a pin crosses a county in full sun and
rains on him and nowhere else. He goes back for the umbrella, the cloud leaves, and the count of dry days goes on.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import clipped

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3163
SLUG = "leave-it-home"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Leave It Home — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show reports a nine-week drought caused by one man who keeps bringing his umbrella, "
    "until he leaves it at home."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a banner across the desk and a PARODY tag in the corner. Vera, older with a "
    "silver bob and half-moon glasses, reports that it has not rained in nine weeks because one man keeps bringing his "
    "umbrella. Gus, with brown curls and an orange jacket, asks why. Farmers have asked the man to leave it at home. A "
    "forecast map fills the screen: an invented county in full sun, one pin marked HIM and a count of 63 dry days. A "
    "tiny cloud crosses the county and rains on the pin and nowhere else. The cloud leaves as he goes back for the "
    "umbrella, the count turns to 64, and Vera says day sixty-four."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
MAP, PIN, COUNTER = "FORECAST", "HIM", "DRY DAYS"
DRY, DRIER = "63", "64"
CLEAR = 1.1  # seconds from the cloud leaving to Vera's last line: the county in the sun, and the room quiet
AFTER = 0.2  # seconds from the cloud leaving to the count turning
TICKER = ("RAIN: NONE IN 9 WEEKS", "RESERVOIRS: LOW", "UMBRELLA: STILL WITH HIM", "FARMERS: LEAVE IT AT HOME")
VERA_NAME, STILL_LIVE = "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, STILL_LIVE, "NINE WEEKS WITHOUT RAIN", True),
    (2, STILL_LIVE, "ONE MAN, ONE UMBRELLA", True),
    (6, STILL_LIVE, "FARMERS ASK HIM TO LEAVE IT AT HOME", True),
    (15, VERA_NAME, "STILL REPORTING", True),
)
END = 24.0
TAIL = 0.8

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "It has not rained here in nine weeks."),
    Line("gus", "Why not?"),
    Line("vera", "One man keeps bringing his umbrella."),
    Line("gus", "Bringing it where?"),
    Line("vera", "Everywhere."),
    Line("gus", "So he's ready."),
    Line("vera", "Farmers have asked him to leave it at home."),
    Line("gus", "Will he?"),
    Line("vera", "He says the one day he does, it'll pour."),
    Line("vera", "This morning, he left it at home."),
    Line("gus", "It's raining!"),
    Line("vera", "On him."),
    Line("gus", "Just him?"),
    Line("vera", "He's gone back for the umbrella."),
    Line("vera", "Day sixty-four."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold = script.say, script.hold
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="side", mouth="flat", arms="chest")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, Pose("level", "flat", head=-2.0))),
    (say(2.1, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", -4.0))),
    (say(2.8, "vera", 2, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(4.82, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", 4.0))),
    (say(5.97, "vera", 4, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(6.87, "gus", 5, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", -3.0))),
    (say(7.82, "desk", 6, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(9.95, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 3.0))),
    (say(10.64, "vera", 8, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(13.19, "phone", 9, *PLACEHOLDER, "map"), Act(READ, LISTEN)),
    (hold(14.99, "phone", "", *PLACEHOLDER, "cloud"), Act(STILL, LISTEN)),
    (say(16.79, "phone", 10, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up"))),
    (say(17.71, "phone", 11, *PLACEHOLDER, "on"), Act(READ, LISTEN)),
    (say(18.46, "phone", 12, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest"))),
    (say(19.26, "phone", 13, *PLACEHOLDER, "gone"), Act(READ, LISTEN)),
    (say(22.06, "vera", 14, *PLACEHOLDER, "day"), Act(Pose("over", "talk"), LISTEN)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST, tail=TAIL)
EVENTS = ("first", "map", "cloud", "on", "gone", "day")
FACES = ((78.0, 565.0, 370.0, 320.0), (540.0, 565.0, 380.0, 320.0))  # both heads, hair included, when the desk is up
POST = InstagramPost(
    title="Have you ever brought an umbrella and stopped the rain?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#umbrella", "#everydaylife", "#relatable"),
    thumbnail=Thumbnail("It's his fault.", 14.2, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, its events happen once and in order, the first picture speaks, the acts match the
    beats, the lower-thirds point at real beats, and no word the reel shows is one the show keeps off it."""
    sketch.check(sk)
    if len(ACTS) != len(sk.beats):
        raise sketch.SketchError(f"{len(ACTS)} acts for {len(sk.beats)} beats")
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the anchor's line")
    if not all(row[0] < len(sk.beats) for row in LOWERS):
        raise sketch.SketchError("a lower-third points past the last beat")
    for text in (
        *(q.text for q in sk.lines),
        *TICKER,
        *(w for row in LOWERS for w in row[1:3]),
        MAP,
        PIN,
        COUNTER,
        POST.title,
        POST.description,
    ):
        news_kit.check_copy(text)


def map_span(beats) -> tuple[float, float]:
    """When the forecast is up: from "This morning" to Vera's last word."""
    return sketch.events(beats, "map")[0][0], sketch.events(beats, "day")[0][0]


def rain_span(beats) -> tuple[float, float]:
    """When the cloud is up: from the held map until just after "He's gone back for the umbrella."."""
    gone = next(i for i, b in enumerate(beats) if b.event == "gone")
    return sketch.events(beats, "cloud")[0][0], beats[gone + 1].start - CLEAR


def overlay(cv, parent, beats, end, measure) -> None:
    """Everything over the picture: the PARODY tag from frame 1, the banner and ticker throughout, the lower-thirds
    except under the map, and the map."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    span = map_span(beats)
    starts = [beats[row[0]].start for row in LOWERS]
    number = 0
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        for left, right in clipped(a, b, (span,)):
            news_inked.lower_third(
                cv, parent, kicker, line, left, right, measure, id=f"news-lower-{number}", slide=slide
            )
            number += 1
    rain = rain_span(beats)
    counts = ((span[0], DRY), (rain[1] + AFTER, DRIER))
    news_inked.forecast_map(cv, parent, MAP, PIN, COUNTER, counts, *span, measure, rain=rain)
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening, a whoosh on the map and rain from when the cloud arrives until it goes, cut dead, and a
    tick on the count. Nothing under the held map: the only rain in the reel is what the county gets."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    start, _ = map_span(beats)
    on, off = rain_span(beats)
    sting = news_kit.write_sting(audio / "sting.wav", [0.0], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05, start], end, seed=seed)
    rain = synth.write_water(audio / "rain.wav", [(on + news_inked.FORECAST_DRIFT, off)], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [off + AFTER], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("rain", 0.0, -18.0, root, rain),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
