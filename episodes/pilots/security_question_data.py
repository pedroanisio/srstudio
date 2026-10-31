"""Security Question — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. Vera reads an error message: incorrect password, a local man's fourth
attempt. He needs a security question. Gus says "Ask me one", and she does. Vera becomes the form and Gus the account
holder: the first pet is correct, why the pet left is not, and the lower-third counts his attempts away. The farm his
mother told him about is marked incorrect twice. Gus's chaos pays off by backfiring: the story is about him, as he
always wanted, and it is his childhood. He asks what happened. His session expires. The reel holds on his face while
the last lower-third gives the farm's reply.

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

SEED = 3122
SLUG = "security-question"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Security Question — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show reports a forgotten password, until the anchor turns into the login form and the "
    "co-host's first pet turns out to be a security problem."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a BREAKING banner across the desk and a PARODY tag in the corner. Vera, older "
    "with a silver bob and half-moon glasses, reads that a local man has an incorrect password on his fourth attempt. "
    "Gus, with brown curls and an orange jacket, offers to answer a security question. She looks over her glasses and "
    "asks about his first pet, Waffles, then why Waffles left. He says a farm. She says incorrect, and a lower-third "
    "counts down his attempts. He asks what happened to Waffles. She says his session has expired. The reel holds on "
    "his face while a lower-third reads that the local farm has no record of Waffles."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
HEADLINE = "LOCAL MAN FORGETS PASSWORD"
COUNTER = "ATTEMPTS REMAINING"
TICKER = ("CAPS LOCK: ON", "PASSWORD HINT: YOU KNOW THIS ONE", "FORGOT PASSWORD: CLICKED TWICE", "ROBOT CHECK: FAILED")
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, "LIVE", HEADLINE, True),
    (3, "GUS BELLOWS, CO-HOST", "VOLUNTEERS", True),
    (4, "ACCOUNT HOLDER", "NOW THE CO-HOST", False),
    (9, COUNTER, "2", True),
    (11, COUNTER, "1", False),
    (16, "LOCAL FARM", "HAS NO RECORD OF WAFFLES", True),  # alone in the hold, on his face
)
END = 27.6

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Incorrect password. A local man's fourth attempt."),
    Line("gus", "So reset it!"),
    Line("vera", "He must now answer a security question."),
    Line("gus", "Easy! Ask me one!"),
    Line("vera", "What was your first pet?"),
    Line("gus", "Waffles!"),
    Line("vera", "Correct. Why did Waffles leave?"),
    Line("gus", "He went to a farm."),
    Line("vera", "Incorrect."),
    Line("gus", "My mom said a farm. With other dogs!"),
    Line("vera", "Incorrect. One attempt remaining."),
    Line("gus", "What happened to Waffles?"),
    Line("vera", "Your session has expired."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
FORM = Pose("over", "talk", head=3.0)
GLARE = Pose("over", "flat", head=3.0)
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, Pose("side", "flat", "phone"))),
    (say(3.3, "desk", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "point", 5.0))),
    (say(4.25, "vera", 2, *PLACEHOLDER), Act(READ, Pose("side", "flat", "rest"))),
    (say(6.55, "gus", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (hold(7.95, "desk", "", *PLACEHOLDER, "stare"), Act(GLARE, Pose("side", "grin", "chest"))),
    (say(9.05, "vera", 4, *PLACEHOLDER), Act(FORM, Pose("side", "grin", "chest"))),
    (say(10.55, "gus", 5, *PLACEHOLDER), Act(GLARE, Pose("wide", "talk", "up", 5.0))),
    (say(11.4, "vera", 6, *PLACEHOLDER), Act(FORM, Pose("side", "grin", "up"))),
    (say(13.5, "gus", 7, *PLACEHOLDER), Act(GLARE, Pose("side", "talk", "chest", -3.0))),
    (say(14.95, "vera", 8, *PLACEHOLDER, "wrong"), Act(FORM, Pose("wide", "gape", "chest"))),
    (say(15.85, "gus", 9, *PLACEHOLDER), Act(GLARE, Pose("wide", "talk", "chest", 5.0))),
    (say(17.85, "vera", 10, *PLACEHOLDER, "again"), Act(FORM, Pose("wide", "gape", "chest"))),
    (hold(20.0, "gus", "", *PLACEHOLDER, "dawn"), Act(GLARE, Pose("down", "flat", "rest"))),
    (say(21.4, "gus", 11, *PLACEHOLDER), Act(GLARE, Pose("level", "talk", "rest"))),
    (hold(22.6, "gus", "", *PLACEHOLDER, "wait"), Act(GLARE, Pose("level", "flat", "rest"))),
    (say(23.8, "gus", 12, *PLACEHOLDER), Act(FORM, Pose("level", "flat", "rest"))),
    (hold(25.35, "gus", "", *PLACEHOLDER, "farm"), Act(GLARE, Pose("wide", "frown", "rest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("first", "stare", "wrong", "again", "dawn", "wait", "farm")
POST = InstagramPost(
    title="What did your parents tell you about your first pet?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#forgotpassword", "#securityquestion", "#everydaylife"),
    thumbnail=Thumbnail(
        "Incorrect password.\nFourth attempt.", 5.0, "News Compiler", focus=(540.0, 400.0), zoom=1.15, place="top"
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
    which take his attempts away and end on the farm's reply."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    starts = [beats[row[0]].start for row in LOWERS]
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        news_inked.lower_third(cv, parent, kicker, line, a, b, measure, slide=slide)
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


ERROR: tuple[synth.Glide, ...] = ((196.0, 196.0, 0.1),)  # a form refusing: sounded twice
ERROR_GAP = 0.15


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening and on the farm's reply, and the form's refusal under each "incorrect"."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    wrong = [sketch.events(beats, event)[0][0] for event in ("wrong", "again")]
    farm = sketch.events(beats, "farm")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, farm + 0.3], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    refused = [at + gap for at in (0.0, *wrong) for gap in (0.0, ERROR_GAP)]
    error = synth.write_tones(audio / "error.wav", refused, end, ERROR)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("error", 0.0, -10.0, root, error),
    ]
