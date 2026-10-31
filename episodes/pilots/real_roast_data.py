"""Real Roast — a pilot of News Compiler, the parody desk, main trigger freshness: the sketch as data.

A real story, from the DoorDash earnings call of 29 October 2026: outside AI agents have placed "several hundred"
orders in total. Vera Stillman reads it with the source on screen. Gus Bellows, who is ordering dinner on his phone
during the news, realises that is about his own number. The numbers are stated straight and only then played with;
every fact traces to ``pilots/news/real-roast/sources.md``. The total and the agents' figure cover different periods,
so nothing here turns them into a share. The turn: the robots are not failing at dinner, they have read the delivery
fee. Gus puts his phone down.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events and every word the reel
shows against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3110
SLUG = "real-roast"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Real Roast — News Compiler"
STORY_DATE = "2026-10-29"
SOURCE = Source(
    "TechCrunch", "Oct 30, 2026", "DoorDash said it's only received 'several hundred' orders from AI agents"
)
DESCRIPTION = (
    "A pilot of a two-anchor parody news show: a straight anchor reports DoorDash's real figure for orders from AI "
    "agents, and her co-host discovers he has personally kept pace with them."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads a story from a source card: outside AI agents have placed several hundred orders with DoorDash in "
    "total. Gus, with red curls and a tangerine jacket, is on his phone and says that is just him. Vera gives the "
    "company's total and Gus escalates: a bathrobe, a driver at his wedding, a second wedding. Vera looks over her "
    "glasses and says the agents may simply have seen the delivery fee. Gus slowly lays his phone face down."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "DOORDASH Q3 TOTAL ORDERS: 993 MILLION",
    "OUTSIDE AI AGENTS: SEVERAL HUNDRED ORDERS, IN TOTAL",
    "SOURCE: Q3 EARNINGS CALL, OCT 29",
)
LOWERS = (  # the beat it arrives on, its kicker, its one line
    (2, "GUS BELLOWS, CO-HOST", "ORDERS PLACED BY GUS: ALSO SEVERAL HUNDRED"),
    (4, "DOORDASH, LAST QUARTER", "993 MILLION TOTAL ORDERS"),
    (5, "GUS BELLOWS, CO-HOST", "CURRENTLY OUTPERFORMING AI, IN A BATHROBE"),
    (7, "GUS BELLOWS, CO-HOST", "KNOWS HIS DRIVER PERSONALLY"),
    (10, "GUS BELLOWS, CO-HOST", "MARRIED TWICE. CATERED TWICE."),
    (12, "VERA STILLMAN, ANCHOR", "IN FAIRNESS"),
    (13, "GUS BELLOWS, CO-HOST", "HAS NOW SEEN THE DELIVERY FEE"),
)
END = 25.0

LINES = (
    Line("vera", "Outside AI agents placed several hundred DoorDash orders. In total."),
    Line("gus", "That's just me!"),
    Line("vera", "Last quarter, DoorDash handled 993 million orders."),
    Line("gus", "So I'm beating the robots. In a bathrobe."),
    Line("vera", "That is not a category."),
    Line("gus", "My driver came to my wedding!"),
    Line("vera", "As a guest?"),
    Line("gus", "He brought the food. To both weddings."),
    Line("vera", "In fairness, the agents may simply have seen the delivery fee."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
TYPING = Pose(eyes="down", arms="phone", mouth="flat")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (
        first(0.0, "vera", 0, "Outside AI agents placed several hundred DoorDash orders.", *PLACEHOLDER, "card"),
        Act(READ, TYPING),
    ),
    (part(3.05, "vera", 0, 8, "In total.", *PLACEHOLDER), Act(READ, TYPING)),
    (say(4.28, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest", -6.0))),
    (first(5.2, "vera", 2, "Last quarter, DoorDash handled", *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (part(6.8, "vera", 2, 4, "993 million orders.", *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (say(9.05, "desk", 3, *PLACEHOLDER), Act(Pose("side", "flat"), Pose("side", "talk", "phone", -4.0))),
    (say(11.35, "vera", 4, *PLACEHOLDER), Act(Pose("over", "talk", head=4.0), Pose("side", "grin", "phone"))),
    (say(12.7, "desk", 5, *PLACEHOLDER), Act(Pose("over", "flat", head=4.0), Pose("wide", "talk", "up", -5.0))),
    (say(14.0, "desk", 6, *PLACEHOLDER), Act(Pose("side", "talk"), Pose("side", "grin", "up"))),
    (first(15.0, "gus", 7, "He brought the food.", *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", 5.0))),
    (part(16.1, "gus", 7, 4, "To both weddings.", *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (hold(17.5, "vera", "", *PLACEHOLDER, "stare"), Act(Pose("level", "flat"), Pose("level", "smirk", "phone"))),
    (say(18.9, "vera", 8, *PLACEHOLDER), Act(Pose("over", "talk", head=3.0), Pose("level", "smirk", "phone"))),
    (hold(22.4, "gus", "", *PLACEHOLDER, "down"), Act(Pose("over", "flat"), Pose("down", "flat", "phone"))),
    (hold(23.6, "gus", "", *PLACEHOLDER, "face-down"), Act(Pose("over", "flat"), Pose("level", "frown", "rest"))),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "stare", "down", "face-down")
POST = InstagramPost(
    title="How many dinners have the robots ordered?",
    description=(
        "Parody desk, real story.\n"
        "TechCrunch, Oct 30, 2026: DoorDash said it's only received 'several hundred' orders from AI agents"
    ),
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#doordash", "#aiagents", "#fooddelivery", "#technews"),
    thumbnail=Thumbnail(
        "Several hundred.\nIn total.", 10.0, "News Compiler", focus=(540.0, 400.0), zoom=1.15, place="top"
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
    if not all(index < len(sk.beats) for index, _, _ in LOWERS):
        raise sketch.SketchError("a lower-third points past the last beat")
    words = (
        *(q.text for q in sk.lines),
        *TICKER,
        *(w for row in LOWERS for w in row[1:]),
        POST.title,
        POST.description,
    )
    for text in words:
        news_kit.check_copy(text)


def spans(beats, end: float) -> list[tuple[float, float, str, str]]:
    """The lower-thirds on a clock: each from its beat to the next one, the last to the end."""
    starts = [beats[index].start for index, _, _ in LOWERS]
    return [(a, b, kicker, line) for a, b, (_, kicker, line) in zip(starts, [*starts[1:], end], LOWERS, strict=True)]


def overlay(cv, parent, beats, end, measure) -> None:
    """Everything over the picture: the corner, the card that goes small, the story's lines and the ticker."""
    news_kit.sign(cv, parent)
    card = sketch.events(beats, "card")[0][0]
    news_kit.ticker(cv, parent, TICKER, card + news_kit.SLIDE, end, measure)  # the card rises through its place first
    for a, b, kicker, line in spans(beats, end):
        news_kit.lower_third(cv, parent, kicker, line, a, b, measure)
    news_kit.bug(cv, parent, 0.0, end, measure)
    small = beats[2].start
    news_kit.source_card(cv, parent, SOURCE, card, small, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting under the opening and on the fee, a whoosh on the card, a stop on the phone put down."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = sketch.events(beats, "face-down")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, at + 0.05], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    tap = synth.write_tones(audio / "tap.wav", [at], end, ((110.0, 80.0, 0.09),))
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tap", 0.0, -6.0, root, tap),
    ]
