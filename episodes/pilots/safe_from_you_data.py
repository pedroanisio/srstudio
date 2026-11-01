"""Safe From You — a real roast of News Compiler, main trigger "wait, did you see this?": the sketch as data.

Hackers took about $6.3 billion from Binance on 29 October 2026, and on 1 November it reopened withdrawals in phases.
Vera reads it flat. Gus has eleven dollars in there and the phone shows the rest: the button that stops working and a
phase with no date. Binance says the loss is its own, so the joke is on a safe you cannot open, never on a customer
who lost money. Every fact traces to ``pilots/news/safe-from-you/sources.md``; the eleven dollars and his bank are the
show's.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :data:`STORY` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import Story

from srstudio import foley as synth
from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3140
SLUG = "safe-from-you"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Safe From You — News Compiler"
STORY_DATE = "2026-11-01"
SOURCE = Source("AFP", "Nov 1, 2026", "Binance says resuming withdrawals after major hack")
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reports the record Binance hack, and her "
    "co-host tries to withdraw his eleven dollars from an account that is safe from everyone, him included."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reads from a source card: hackers took six billion dollars from Binance. Gus, with red curls and a "
    "tangerine jacket, says his bank takes three days. A phone shows a plain money app with a balance of eleven "
    "dollars and a withdraw button. A finger taps it and it greys out to suspended. Later a note on the phone reads "
    "no date. Gus asks who his money is safe from. Vera lowers her glasses and looks into the camera: you."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = (
    "STOLEN: ABOUT $6.3 BILLION",
    "BINANCE: THE LOSSES WILL NOT BE PASSED ON TO USERS",
    "PHASE ONE OF WITHDRAWALS: SUNDAY, BITCOIN FIRST",
)
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
APP, BALANCE, ACTION, REFUSED = "MY MONEY", "$11.00", "WITHDRAW", "SUSPENDED"
NOTES = ("PHASE ONE: BITCOIN FIRST", "YOUR PHASE: NO DATE")
TAPS = (0.3, 0.7, 1.05)  # after the app comes up, faster each time
LOWERS = (  # a name only while that anchor speaks or fills the shot
    (2, GUS_NAME, "TAKING THIS PERSONALLY"),
    (3, VERA_NAME, "BINANCE: \"YOUR ASSETS ARE SAFE\""),
    (4, GUS_NAME, "LONG-TERM INVESTOR, $11"),
    (7, STILL_LIVE, "WITHDRAWALS REOPEN IN PHASES"),
    (8, GUS_NAME, "PHASE UNKNOWN"),
    (10, STILL_LIVE, 'BINANCE: "YOUR ASSETS ARE SAFE"'),
    (13, VERA_NAME, "STILL REPORTING"),
)
END = 26.4

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Hackers took six billion dollars from Binance."),
    Line("vera", "Most of it in about twenty minutes."),
    Line("gus", "Twenty minutes? My bank takes three days!"),
    Line("vera", 'Binance told customers, "Your assets are safe."'),
    Line("gus", "Good! I've got eleven dollars in there."),
    Line("vera", "Withdrawals were suspended."),
    Line("vera", "Sunday they reopened, in phases."),
    Line("gus", "What phase is eleven dollars?"),
    Line("vera", "Later phases have no date."),
    Line("gus", "But my money's safe."),
    Line("vera", "Yes."),
    Line("gus", "Safe from who?"),
    Line("vera", "You."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold = script.say, script.hold
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="side", mouth="flat", arms="chest")
LOW = Pose("over", "flat", head=3.0)  # the glasses down, the stare
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "card"), Act(READ, Pose("level", "flat", head=-2.0))),
    (say(2.5, "vera", 1, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(4.3, "gus", 2, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -5.0))),
    (say(6.8, "vera", 3, *PLACEHOLDER), Act(READ, Pose("side", "grin", "chest"))),
    (say(9.2, "gus", 4, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "up", -4.0))),
    (hold(11.2, "phone", "", *PLACEHOLDER, "app"), Act(STILL, LISTEN)),
    (say(13.5, "phone", 5, *PLACEHOLDER, "refused"), Act(READ, LISTEN)),
    (say(15.1, "desk", 6, *PLACEHOLDER), Act(READ, Pose("wide", "gape", "chest"))),
    (say(17.2, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "up", 4.0))),
    (say(18.9, "phone", 8, *PLACEHOLDER, "phase"), Act(READ, LISTEN)),
    (say(20.6, "gus", 9, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest", -3.0))),
    (say(21.9, "vera", 10, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(22.7, "gus", 11, *PLACEHOLDER), Act(STILL, Pose("side", "talk", "chest", 4.0))),
    (hold(23.75, "vera", "", *PLACEHOLDER, "stare"), Act(LOW, LISTEN)),
    (say(25.0, "vera", 12, *PLACEHOLDER, "you"), Act(Pose("over", "talk"), LISTEN)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "app", "refused", "phase", "stare", "you")
POST = InstagramPost(
    title="Safe from who?",
    description=f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#binance", "#crypto", "#parodynews", "#technews"),
    thumbnail=Thumbnail("Your money is safe.", 14.6, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST, parody=True)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks, the words on the phone among them."""
    STORY.validate(sk, (APP, BALANCE, ACTION, REFUSED, *NOTES))


def apps(beats) -> tuple[tuple[float, float], tuple[float, float]]:
    """When the app is up: the taps and the line that stops them, then the line that gives his phase no date."""
    app = sketch.events(beats, "app")[0][0]
    refused = sketch.events(beats, "refused")[0][0]
    phase = sketch.events(beats, "phase")[0][0]
    return (app, next(b.start for b in beats if b.start > refused)), (
        phase,
        next(b.start for b in beats if b.start > phase),
    )


def taps(beats) -> tuple[float, ...]:
    """The seconds his finger lands."""
    app = sketch.events(beats, "app")[0][0]
    return tuple(round(app + at, 3) for at in TAPS)


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words, and the app over them, twice."""
    first, second = apps(beats)
    refused = sketch.events(beats, "refused")[0][0]

    def phone() -> None:
        news_inked.money_app(
            cv, parent, APP, BALANCE, ACTION, REFUSED, *first, measure, taps=taps(beats), refused_at=refused
        )
        news_inked.money_app(
            cv,
            parent,
            APP,
            BALANCE,
            ACTION,
            REFUSED,
            *second,
            measure,
            refused_at=second[0],
            notes=((second[0], NOTES[0]), (round(second[0] + 0.5, 3), NOTES[1])),
            id="news-money-app-again",
        )

    STORY.overlay(cv, parent, beats, end, measure, (first, second), phone)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and after the last word, a whoosh on the card and the app, a tick on each tap. Nothing
    under the stare: the room goes quiet before "You."."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    first, second = apps(beats)
    you = sketch.events(beats, "you")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, you + 0.55], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05, first[0], second[0]], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", list(taps(beats)), end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
