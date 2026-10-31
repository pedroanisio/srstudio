"""One More Episode — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. Gus is mid-rant from the first frame: nobody means one more episode. Vera
reports a local couple who said it seven episodes ago, about a show neither of them likes. She tries to end the
bulletin and Gus says "one more update", and the small choice repeats: the lower-third counts the updates, 1, 2, then
38. Gus's chaos pays off by spreading: he has caught what they have. The television asks if they are still watching,
a countdown runs to the next update, Vera lowers her glasses to the lens, and at 0 the reel cuts back to its first
frame, because the loop is the joke.

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

SEED = 3121
SLUG = "one-more-episode"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "One More Episode — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show reports a couple watching a show neither of them likes, until the co-host will not "
    "let the bulletin end either."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Gus, with "
    "brown curls and an orange jacket, says nobody means one more episode. Vera, older with a silver bob and half-moon "
    "glasses, reports a couple who said it seven episodes ago about a show neither likes, with the remote out of "
    "reach. She tries to end the bulletin and Gus demands one more update, again and again, while a lower-third counts "
    "the updates up to 38. A countdown runs, Vera lowers her glasses to the viewer and asks are you, and the reel cuts "
    "back to its first frame."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
HEADLINE = "LOCAL COUPLE SAY 'ONE MORE EPISODE'"
TICKER = ("SNACKS: GONE", "SLEEP: POSTPONED", "PLOT: LOST AT EPISODE 2", "ALARM: SET, FOR SOME REASON")
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, "LIVE", HEADLINE, False),  # settled from frame 1: the last picture is the first
    (1, "THE TIMELINE", "SAID IT 7 EPISODES AGO", True),
    (4, "CRITICAL RECEPTION", "NEITHER OF THEM LIKES IT", True),
    (5, "THE REMOTE", "3 FEET AWAY", True),
    (6, "VERA STILLMAN, ANCHOR", "SIGNING OFF", True),
    (7, "LIVE UPDATE 1", "BULLETIN EXTENDED, ONE TIME ONLY", True),
    (10, "LIVE UPDATE 2", "BULLETIN EXTENDED, ONE LAST TIME", False),
    (12, "LIVE UPDATE 38", "BULLETIN NOW IN ITS SIXTH HOUR", False),
    (13, "LIVE UPDATE 38", "NEXT UPDATE IN 3", False),
    (14, "LIVE UPDATE 38", "NEXT UPDATE IN 2", False),
    (15, "LIVE UPDATE 38", "NEXT UPDATE IN 1", False),
    (16, "LIVE", HEADLINE, False),  # 0: the first frame again
)
END = 24.9
TAIL = 0.9  # the first picture again, long enough for its strap to pass the legibility check

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("gus", "Nobody means one more episode!"),
    Line("vera", "A local couple said it seven episodes ago."),
    Line("gus", "It must be incredible!"),
    Line("vera", "Neither of them likes it."),
    Line("gus", "Then turn it off!"),
    Line("vera", "The remote is out of reach. Talks have collapsed."),
    Line("vera", "That's all the time we have."),
    Line("gus", "One more update!"),
    Line("vera", "The television has asked if they're still watching."),
    Line("gus", "How dare it! One more!"),
    Line("vera", "Their alarm goes off in one hour."),
    Line("gus", "One more!"),
    Line("vera", "Are you?"),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
OPENING = Pose("wide", "talk", "up", -5.0)
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "gus", 0, *PLACEHOLDER, "first"), Act(STILL, OPENING)),
    (say(1.85, "vera", 1, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "up"))),
    (say(4.4, "gus", 2, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest", 4.0))),
    (say(5.9, "vera", 3, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (say(7.5, "desk", 4, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(8.75, "vera", 5, *PLACEHOLDER), Act(READ, Pose("side", "frown", "rest"))),
    (say(11.75, "desk", 6, *PLACEHOLDER), Act(READ, Pose("wide", "flat", "rest"))),
    (say(13.5, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", 5.0))),
    (say(14.75, "desk", 8, *PLACEHOLDER), Act(READ, Pose("side", "flat", "phone"))),
    (first(17.4, "gus", 9, "How dare it!", *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", -5.0))),
    (part(18.25, "gus", 9, 3, "One more!", *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "up", 5.0))),
    (say(19.1, "vera", 10, *PLACEHOLDER), Act(READ, Pose("side", "grin", "phone"))),
    (say(21.0, "desk", 11, *PLACEHOLDER), Act(Pose("level", "flat"), Pose("squint", "talk", "up", -5.0))),
    (hold(21.9, "vera", "", *PLACEHOLDER, "three"), Act(Pose("level", "flat"), Pose("squint", "grin", "phone"))),
    (
        hold(22.86, "vera", "", *PLACEHOLDER, "two"),
        Act(Pose("over", "flat", head=3.0), Pose("squint", "grin", "phone")),
    ),
    (say(23.76, "vera", 12, *PLACEHOLDER, "one"), Act(Pose("over", "talk", head=3.0), Pose("squint", "grin", "phone"))),
    (hold(24.66, "gus", "", *PLACEHOLDER, "loop"), Act(STILL, OPENING)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST, tail=TAIL)
EVENTS = ("first", "three", "two", "one", "loop")
FACES = ((300.0, 475.0, 490.0, 385.0),)  # Vera's head on the cover's frame: its headline stays off it
POST = InstagramPost(
    title="What are you still watching that you don't even like?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#bingewatching", "#onemoreepisode", "#everydaylife"),
    thumbnail=Thumbnail(
        "One more episode.\nSeven episodes ago.", 3.0, "News Compiler", focus=(540.0, 400.0), zoom=1.6, place="top"
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
        raise sketch.SketchError("the reel opens on the co-host's line")
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
    which count the updates and then down to the cut."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure, slide=False)
    starts = [beats[row[0]].start for row in LOWERS]
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        news_inked.lower_third(cv, parent, kicker, line, a, b, measure, slide=slide)
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening, which the loop plays again, and a tick on each second of the countdown."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    counts = [sketch.events(beats, event)[0][0] for event in ("three", "two", "one", "loop")]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", counts, end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
