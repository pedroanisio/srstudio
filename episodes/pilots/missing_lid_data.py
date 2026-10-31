"""Missing Lid — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. A mock-solemn missing-person appeal for a storage lid, with a flyer beside
Vera's head. The drawer holds forty containers and no lids; it was last seen at a potluck, and nobody comes back from a
potluck. Gus's chaos pays off by turning sincere: he mocks the appeal, then makes it. Vera closes on the false tease of
every local bulletin: coming up at eleven, one sock.

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

SEED = 3124
SLUG = "missing-lid"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Missing Lid — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show makes a solemn missing-person appeal for a storage lid, until the co-host starts to "
    "mean it."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Vera, older "
    "with a silver bob and half-moon glasses, asks if you have seen this lid, beside a flyer reading MISSING with a "
    "picture of a storage lid. Gus, with brown curls and an orange jacket, scoffs. Vera says the drawer holds forty "
    "containers and no lids, and it was last seen at a potluck. Gus scoffs that it is plastic, then pleads for the lid "
    "to come home. Vera warns not to microwave it, and teases one sock at eleven."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = ("DRAWER: STILL WON'T CLOSE", "BASE: FOUND", "FOIL: HOLDING THE LINE", "ICE CREAM TUB: NOT ICE CREAM")
CARD = "ONE LID"
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, "POLICE APPEAL", "LAST SEEN INTACT", True),
    (2, "DRAWER CENSUS", "40 CONTAINERS, 0 LIDS", True),
    (4, "LAST SEEN", "LEAVING WITH A CASSEROLE", True),
    (6, "THE CONTAINER", "SAYS NOTHING, SEALS NOTHING", True),
    (9, "GUS BELLOWS, CO-HOST", "MAKING A DIRECT APPEAL", True),
    (10, "REWARD", "ONE MATCHING BOWL", True),
    (11, "COMING UP", "ONE SOCK", True),
)
END = 24.0

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Have you seen this lid?"),
    Line("gus", "Check the drawer!"),
    Line("vera", "The drawer holds forty containers and no lids."),
    Line("gus", "Who lives like this?"),
    Line("vera", "Everyone. It was last seen at a potluck."),
    Line("gus", "Nobody comes back from a potluck!"),
    Line("vera", "Its container has not given up hope."),
    Line("gus", "It's plastic!"),
    Line("vera", "The family has left one shelf empty."),
    Line("gus", "Come home, little lid!"),
    Line("vera", "If found, do not microwave. Coming up at eleven: one sock."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, STILL)),
    (say(1.5, "desk", 1, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 4.0))),
    (say(2.6, "vera", 2, *PLACEHOLDER), Act(READ, Pose("squint", "flat", "chest"))),
    (say(5.2, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(6.4, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "flat", "rest"))),
    (say(8.9, "desk", 5, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(10.8, "vera", 6, *PLACEHOLDER), Act(READ, Pose("side", "frown", "rest"))),
    (say(13.0, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "up", 5.0))),
    (say(14.2, "vera", 8, *PLACEHOLDER), Act(READ, Pose("wide", "frown", "rest"))),
    (say(16.5, "gus", 9, *PLACEHOLDER, "plea"), Act(STILL, Pose("shut", "talk", "chest", 3.0))),
    (first(17.9, "vera", 10, "If found, do not microwave.", *PLACEHOLDER), Act(READ, Pose("shut", "frown", "chest"))),
    (part(20.0, "vera", 10, 5, "Coming up at eleven: one sock.", *PLACEHOLDER, "tease"), Act(READ, STILL)),
    (hold(22.75, "vera", "", *PLACEHOLDER, "last"), Act(Pose("level", "flat"), STILL)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("first", "plea", "tease", "last")
FACES = ((300.0, 475.0, 490.0, 385.0),)  # Vera's head on the cover's frame: its headline stays off it
POST = InstagramPost(
    title="How many containers in your drawer have a lid?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#kitchenlife", "#tupperwaredrawer", "#everydaylife"),
    thumbnail=Thumbnail("Have you seen\nthis lid?", 1.0, "News Compiler", focus=(720.0, 400.0), zoom=1.7, place="top"),
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
    """Everything over the picture: the PARODY tag from frame 1, the banner and ticker throughout, the lower-thirds, and
    the flyer beside Vera on her close-ups of the appeal, which stop at the plea."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    starts = [beats[row[0]].start for row in LOWERS]
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        news_inked.lower_third(cv, parent, kicker, line, a, b, measure, slide=slide)
    plea = sketch.events(beats, "plea")[0][0]
    for i, (beat, after) in enumerate(zip(beats, beats[1:], strict=False)):
        if beat.who == "vera" and beat.start < plea:
            news_inked.missing_card(cv, parent, CARD, beat.start, after.start, measure, id=f"news-missing-card-{i}")
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening and after the tease."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    last = sketch.events(beats, "last")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, last + 0.1], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    return [sketch.effect("sting", 0.0, -12.0, root, sting), sketch.effect("whoosh", 0.0, -14.0, root, whoosh)]
