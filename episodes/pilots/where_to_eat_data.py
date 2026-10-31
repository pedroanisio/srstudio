"""Where to Eat — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. Election-night coverage of a couple choosing dinner: too close to call,
both candidates say they don't mind, and she has ruled out everything. The lower-third is the results board. Gus's
chaos pays off by being ignored: "Order anything!" is how they get cereal. The board holds at zeros before the call,
and the reel cuts hard on "landslide".

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

SEED = 3123
SLUG = "where-to-eat"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Where to Eat — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show covers a couple choosing where to eat as if it were election night, until the "
    "results come in."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Vera, older "
    "with a silver bob and half-moon glasses, calls where to eat too close to call. Gus, with brown curls and an "
    "orange jacket, shouts at the candidates to pick one. Both say they don't mind, and she has ruled out Thai, pizza "
    "and that place. Hunger rises. Vera projects a winner, and a lower-third results board holds at zero for "
    "everything. Vera says cereal, in a landslide, and the board reads cereal two, everything else zero."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = ("TURNOUT: 2", "FRIDGE: NO COMMENT", "DELIVERY APP: OPEN FOR 40 MINUTES", "THAT PLACE: KNOWS WHAT IT DID")
RESULTS = "RESULTS"
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, "TONIGHT'S RACE", "WHERE TO EAT", True),
    (2, "THE CANDIDATES", "BOTH FINE WITH ANYTHING", True),
    (4, "RULED OUT SO FAR", "3 PLACES, 0 REASONS", True),
    (6, "THAT PLACE", "REASON WITHHELD", True),
    (8, "NOW 9:40 P.M.", "NOTHING ORDERED", True),
    (10, "ALL VOTES IN", "2 OF 2 REPORTING", True),
    (12, RESULTS, "THAI 0, PIZZA 0, THAT PLACE 0", False),  # the hold: it snaps, as a board does
    (13, RESULTS, "CEREAL 2, EVERYTHING ELSE 0", False),
)
END = 20.5
TAIL = 0.0  # a hard cut on "landslide"

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Where to eat is too close to call."),
    Line("gus", "Just pick one!"),
    Line("vera", "Both candidates say they don't mind."),
    Line("gus", "Then it's over!"),
    Line("vera", "She has ruled out Thai, pizza, even that place."),
    Line("gus", "What's wrong with that place?"),
    Line("vera", "He should know."),
    Line("gus", "He doesn't know!"),
    Line("vera", "Hunger is now up in every district."),
    Line("gus", "Order anything!"),
    Line("vera", "We can now project a winner."),
    Line("gus", "Who?"),
    Line("vera", "Cereal. In a landslide."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold = script.say, script.hold
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "desk", 0, *PLACEHOLDER, "first"), Act(READ, Pose("wide", "gape", "up", -5.0))),
    (say(2.2, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(3.3, "vera", 2, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (say(5.5, "desk", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(6.6, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "frown", "rest"))),
    (say(9.6, "gus", 5, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 4.0))),
    (say(10.95, "vera", 6, *PLACEHOLDER), Act(Pose("over", "talk", head=3.0), Pose("squint", "flat", "chest"))),
    (say(12.05, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", 5.0))),
    (say(13.15, "vera", 8, *PLACEHOLDER), Act(READ, Pose("side", "flat", "rest"))),
    (say(15.25, "desk", 9, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(16.25, "desk", 10, *PLACEHOLDER), Act(READ, Pose("side", "flat", "rest"))),
    (say(18.05, "gus", 11, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest", -3.0))),
    (hold(18.7, "desk", "", *PLACEHOLDER, "board"), Act(Pose("level", "flat"), Pose("side", "frown", "chest"))),
    (say(20.2, "vera", 12, *PLACEHOLDER, "call"), Act(READ, Pose("side", "frown", "chest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST, tail=TAIL)
EVENTS = ("first", "board", "call")
FACES = ((145.0, 640.0, 240.0, 250.0), (610.0, 640.0, 260.0, 250.0))  # both heads on the cover's frame, kept clear
POST = InstagramPost(
    title="Who in your house says 'I don't mind' and means it?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#whattoeat", "#couplelife", "#everydaylife"),
    thumbnail=Thumbnail(
        "Where to eat?\nToo close to call.", 1.5, "News Compiler", focus=(540.0, 400.0), zoom=1.15, place="top"
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
    which are the results board and snap to the call."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    starts = [beats[row[0]].start for row in LOWERS]
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        news_inked.lower_third(cv, parent, kicker, line, a, b, measure, slide=slide)
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening, a tick as the board stops and another on the call; nothing after the cut."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    board = sketch.events(beats, "board")[0][0]
    call = sketch.events(beats, "call")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [board, call], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
