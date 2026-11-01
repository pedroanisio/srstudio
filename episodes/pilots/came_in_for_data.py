"""What She Came In For — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. The show is live outside a kitchen, because a woman walked in and forgot
why; the live shot beside Vera is a door nothing happens at. It plays as a mystery with one fair clue: Gus shouts advice
down the lens at her, she goes back to the couch, and the television there is on. It comes back to her. She came in to
get away from him. Gus's chaos pays off by being the answer to the story he is covering: the louder he helps, the more
he proves it. His "Ma'am!" comes back small, the door slams, and Vera closes the case with the opening's kitchen, which
now has a reason.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events and every word the reel
shows against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Hold, Pose
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3127
SLUG = "came-in-for"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "What She Came In For — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show goes live outside a kitchen, where a woman has forgotten why she walked in, until "
    "the reason turns out to be sitting at the desk."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Vera, older "
    "with a silver bob and half-moon glasses, reports live outside a kitchen, where a woman has forgotten why she "
    "walked in. Gus, with brown curls and an orange jacket, shouts advice at her down the lens. She tries the fridge "
    "and a spoon, then goes back to the couch, where the television is on. It comes back to her: she came in to get "
    "away from Gus. He says ma'am, very small. The door in the live shot beside Vera slams, and she reports that the "
    "woman is back in the kitchen, and knows why."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"news-vera": 3, "news-gus": 3}
DOOR = "KITCHEN"
SMALL = -9.11864  # dB, 35% of the full voice: the same word he shouted, with the air gone out of it
SLAM = 0.35  # seconds into the held beat at which the door shuts: long enough to see it open first
TICKER = ("FRIDGE: OPENED 3 TIMES", "LIGHTS: LEFT ON", "HALLWAY: NO COMMENT", "HER TV: STILL ON, VERY LOUD")
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, "LIVE: OUTSIDE A KITCHEN", "SHE FORGOT WHY SHE CAME IN", True),
    (2, "TIME INSIDE", "4 MINUTES, 0 LEADS", True),
    (4, "THE FRIDGE", "RULED OUT", True),
    (6, "THE SPOON", "UNRELATED", True),
    (7, "GUS BELLOWS, CO-HOST", "ADVISING HER DIRECTLY", True),
    (8, "THE COUCH", "TV ON, VERY LOUD", True),
    (11, "CASE CLOSED", "THE REASON: GUS", False),  # it snaps, as the answer does
)
END = 26.6
TAIL = 0.0

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "We're live outside a kitchen."),
    Line("gus", "Why?"),
    Line("vera", "She walked in. She forgot why."),
    Line("gus", "What did she come in for?"),
    Line("vera", "It's not in the fridge."),
    Line("gus", "It's never in the fridge!"),
    Line("vera", "She's holding a spoon. It means nothing."),
    Line("gus", "Ma'am! Back to the couch! Think!"),
    Line("vera", "She's on the couch. The TV's on. It's coming back."),
    Line("gus", "Ma'am, what was it?"),
    Line("vera", "To get away from you."),
    Line("gus", "Ma'am?", gain=SMALL),
    Line("vera", "She's back in the kitchen. She knows why."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold = script.say, script.hold
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
TURNED = Act(Pose("over", "flat"), Pose("wide", "gape", "chest"), (Hold("vera", "gus", "close"),))
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, STILL)),
    (say(1.7, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", 4.0))),
    (say(2.6, "vera", 2, *PLACEHOLDER), Act(READ, Pose("squint", "flat", "chest"))),
    (say(4.9, "desk", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(6.5, "vera", 4, *PLACEHOLDER), Act(READ, Pose("side", "flat", "rest"))),
    (say(8.0, "gus", 5, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(9.4, "vera", 6, *PLACEHOLDER), Act(READ, Pose("squint", "flat", "chest"))),
    (say(12.0, "gus", 7, *PLACEHOLDER, "lens"), Act(STILL, Pose("wide", "talk", "up", 5.0))),
    (say(14.3, "vera", 8, *PLACEHOLDER), Act(READ, Pose("wide", "flat", "chest"))),
    (say(17.6, "gus", 9, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    # the hold on "turn" keeps Vera on Gus through "reason", the one line she says to him, and through the slam; "close"
    # is her turn back to camera
    (hold(19.0, "desk", "", *PLACEHOLDER, "turn"), TURNED),
    (say(20.4, "desk", 10, *PLACEHOLDER, "reason"), Act(Pose("over", "talk"), Pose("wide", "gape", "chest"))),
    (say(22.0, "gus", 11, *PLACEHOLDER, "small"), Act(STILL, Pose("side", "talk", "rest"))),
    (hold(23.0, "vera", "", *PLACEHOLDER, "slam"), Act(STILL, Pose("side", "frown", "rest"))),
    (say(23.8, "vera", 12, *PLACEHOLDER, "close"), Act(READ, Pose("side", "frown", "rest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST, tail=TAIL)
EVENTS = ("first", "lens", "turn", "reason", "small", "slam", "close")
FACES = ((78.0, 565.0, 370.0, 320.0), (540.0, 565.0, 380.0, 320.0))  # both heads, hair included, on the cover's frame
POST = InstagramPost(
    title="What do you do when you forget why you walked in?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#whydidicomeinhere", "#everydaylife", "#relatable"),
    thumbnail=Thumbnail(
        "We're live outside\na kitchen", 5.2, "News Compiler", focus=(495.0, 400.0), zoom=1.28, place="top"
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
    """Everything over the picture: the PARODY tag from frame 1, the banner and ticker throughout, the lower-thirds, the
    last of which snaps to the answer, and the live door beside Vera on every close-up of hers, ajar until it slams."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    starts = [beats[row[0]].start for row in LOWERS]
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        news_inked.lower_third(cv, parent, kicker, line, a, b, measure, slide=slide)
    slam = sketch.events(beats, "slam")[0][0]
    for i, (beat, after) in enumerate(zip(beats, [*beats[1:], None], strict=True)):
        if beat.who == "vera" and beat.start < slam:
            news_inked.live_door(cv, parent, DOOR, beat.start, after.start, measure, id=f"news-live-door-{i}")
    news_inked.live_door(cv, parent, DOOR, slam, end, measure, shut=slam + SLAM, id="news-live-door-last")
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening, a tick as the answer snaps in, and the door; nothing after the cut."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    turn = sketch.events(beats, "reason")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [turn], end)
    door = synth.write_bursts(
        audio / "door.wav", [sketch.events(beats, "slam")[0][0] + SLAM], end, synth.SLAM, seed=seed
    )
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
        sketch.effect("door", 0.0, -6.0, root, door),
    ]
