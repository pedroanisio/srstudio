"""You Too — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. Vera Stillman reads a twelve-year-old slip as a transcript: the waiter said
enjoy your meal, the local man said you too. Gus Bellows cannot see why it is news until he sees that it is. A counter
on the lower-third gives the days since the incident. Then Gus wishes Vera a happy birthday, which the ticker has been
saying all along, and she says it. Nobody speaks. The counter goes to 0. Gus's chaos pays off by winning: he says
"Three a.m., Vera", and the reel holds on her.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events and every word the reel
shows against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3120
SLUG = "you-too"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "You Too — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show reports a man who told a waiter 'you too' twelve years ago, until the unflappable "
    "anchor does it herself, on air, on her own birthday."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Vera, older "
    "with a silver bob and half-moon glasses, reads that a waiter said enjoy your meal and a local man said you too. "
    "Gus, with brown curls and an orange jacket, is outraged. A lower-third counts 4,383 days since the incident. Vera "
    "adds that the man thinks about it every night and has told his bank he loves them. Gus wishes Vera a happy "
    "birthday and she answers you too. She freezes, her eyes wide, and the counter drops to 0. Gus says three a.m., "
    "Vera."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
HEADLINE = "LOCAL MAN TELLS WAITER 'YOU TOO'"
COUNTER = "DAYS SINCE INCIDENT"
TICKER = ("WAITER: RECALLS NOTHING", "TODAY'S BIRTHDAYS: VERA STILLMAN", "MEAL: ENJOYED", "LOCAL MAN: STILL AWAKE")
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, "LIVE", HEADLINE, True),
    (2, COUNTER, "4,383", True),
    (4, "THE SUSPECT", "AWAKE, REPLAYING IT", True),
    (5, "EXPERT ADVICE", "LET IT GO", True),
    (7, "ALSO ON FILE", "TOLD HIS BANK 'LOVE YOU'", True),
    (11, COUNTER, "4,383", True),
    (13, COUNTER, "0", False),  # the silence: it snaps, as a counter does
)
END = 27.0

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Waiter: enjoy your meal. Man: you too."),
    Line("gus", "The waiter isn't eating!"),
    Line("vera", "The incident took place twelve years ago."),
    Line("gus", "Then why is it news?"),
    Line("vera", "He thinks about it every night at three a.m."),
    Line("gus", "Let it go, man!"),
    Line("vera", "Last week, he ended a call to his bank with, love you."),
    Line("gus", "Did they say it back?"),
    Line("vera", "They asked if there was anything else."),
    Line("gus", "Anyway. Happy birthday, Vera."),
    Line("vera", "You too."),
    Line("gus", "Three a.m., Vera."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, Pose("wide", "gape", "chest"))),
    (say(3.35, "desk", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(4.7, "vera", 2, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "up"))),
    (say(7.0, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 4.0))),
    (say(8.25, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "frown", "chest"))),
    (say(10.75, "desk", 5, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (first(11.85, "vera", 6, "Last week, he ended a call to his bank", *PLACEHOLDER), Act(READ, Pose("side", "flat"))),
    (part(14.1, "vera", 6, 9, "with, love you.", *PLACEHOLDER), Act(READ, Pose("wide", "gape"))),
    (say(15.1, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest", -3.0))),
    (say(16.45, "desk", 8, *PLACEHOLDER), Act(READ, Pose("side", "frown", "rest"))),
    (hold(18.4, "desk", "", *PLACEHOLDER, "look"), Act(Pose("level", "flat"), Pose("side", "flat", "rest", 4.0))),
    (say(19.5, "gus", 9, *PLACEHOLDER), Act(Pose("level", "flat"), Pose("side", "talk", "rest", 4.0))),
    (say(21.6, "vera", 10, *PLACEHOLDER, "slip"), Act(Pose("level", "talk"), Pose("side", "flat", "rest"))),
    (hold(22.3, "vera", "", *PLACEHOLDER, "zero"), Act(Pose("wide", "flat"), Pose("side", "smirk", "rest"))),
    (say(24.2, "desk", 11, *PLACEHOLDER, "button"), Act(Pose("wide", "flat"), Pose("side", "talk", "chest", 4.0))),
    (hold(25.55, "vera", "", *PLACEHOLDER, "last"), Act(Pose("wide", "flat"), Pose("side", "smirk", "rest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("first", "look", "slip", "zero", "button", "last")
POST = InstagramPost(
    title="What's the 'you too' you still think about at 3 a.m.?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#awkwardmoments", "#overthinking", "#everydaylife"),
    thumbnail=Thumbnail(
        "Enjoy your meal.\nYou too.", 5.2, "News Compiler", focus=(540.0, 400.0), zoom=1.15, place="top"
    ),
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
        POST.title,
        POST.description,
    ):
        news_kit.check_copy(text)


def overlay(cv, parent, beats, end, measure) -> None:
    """Everything over the picture: the PARODY tag from frame 1, the banner and ticker throughout, and the lower-thirds,
    the last of them the counter back at 0."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    starts = [beats[row[0]].start for row in LOWERS]
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        news_inked.lower_third(cv, parent, kicker, line, a, b, measure, slide=slide)
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening and after the button, and one tick on the counter's reset, alone in the silence."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    zero = sketch.events(beats, "zero")[0][0]
    last = sketch.events(beats, "last")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, last + 0.05], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [zero], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
