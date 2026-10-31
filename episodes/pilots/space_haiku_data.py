"""Space Haiku — a real roast of News Compiler, main trigger "wait, did you see this?": the sketch as data.

Google's first Project Suncatcher satellite answered its first prompt from orbit on 30 October 2026, with a haiku. Gus
is already in tears on the first frame. Vera reads the poem flat, then what it runs on: four chips, one at a time,
about twenty minutes. He takes that for an artist's life until she mentions the limericks. She closes the story in a
haiku of her own about him. Every fact traces to ``pilots/news/space-haiku/sources.md``; the tears are the show's.

``SKETCH`` is checked by :func:`srstudio.sketch.check`; :data:`STORY` checks the events and every word the reel shows
against :func:`srstudio.news_kit.check_copy`. ``ACTS`` runs parallel to the beats.
"""

from __future__ import annotations

from dataclasses import replace

from news_story import Story

from srstudio import foley as synth
from srstudio import news_kit, scripting, sketch
from srstudio.news_kit import Act, Pose, Source
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3121
SLUG = "space-haiku"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Space Haiku — News Compiler"
STORY_DATE = "2026-10-30"
SOURCE = Source("TechCrunch", "Oct 30, 2026", "Google's first data center satellite is online and writing poetry")
DESCRIPTION = (
    "A real roast from a two-anchor parody news show: a straight anchor reads the haiku Google's first data center "
    "satellite wrote, her co-host weeps, and she closes the story with a haiku about him."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk in front of a bright monitor wall. Vera, older with a silver bob and half-moon "
    "glasses, reports that Google's satellite wrote a haiku. Gus, with red curls and a tangerine jacket, is already "
    "crying and asks her to read it again. She reads it flat. He asks who hurt it. She gives the chips and the twenty "
    "minutes, then the limericks, and he feels betrayed. She closes with a haiku about him in tears."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
TICKER = ("PROJECT SUNCATCHER: FIRST RESPONSE FROM ORBIT", "ON BOARD: FOUR TPUS, ONE ON AT A TIME", "POWER: UP TO 1 KW")
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # a name only while that anchor speaks or fills the shot
    (1, GUS_NAME, "PREVIOUSLY FINE"),
    (2, "FROM ORBIT", "THE SATELLITE'S HAIKU, IN FULL"),
    (6, GUS_NAME, "SEEKING ANSWERS"),
    (7, VERA_NAME, "ONE CHIP AT A TIME"),
    (8, GUS_NAME, "SOMEONE GET IT A BLANKET"),
    (9, VERA_NAME, "SPACE-THEMED LIMERICKS: CONFIRMED"),
    (10, GUS_NAME, "FEELS BETRAYED"),
    (11, STILL_LIVE, "CO-HOST UPDATE"),
    (14, "HAIKU BY", VERA_NAME),
)
END = 28.1

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Google's first data center satellite wrote a haiku."),
    Line("gus", "Please. Read it again."),
    Line("vera", "Blue marble below. Data streams in silent grace. Starlight feeds my core."),
    Line("gus", "Who hurt this thing?"),
    Line("vera", "Four chips, one at a time, about twenty minutes."),
    Line("gus", "Twenty minutes, then a lie-down? That's a poet!"),
    Line("vera", "Google also tested space limericks."),
    Line("gus", "Limericks? This morning it was an artist!"),
    Line("vera", "Co-host in tears now. The satellite feels nothing. Back after the break."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold, first, part = script.say, script.hold, script.first, script.part
READ = Pose(mouth="talk")
FLAT = Pose(mouth="flat")
CRY = Pose("weep", "frown", "chest")
SOB = Pose("weep", "talk", "chest", -3.0)
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "desk", 0, *PLACEHOLDER, "card"), Act(READ, CRY)),
    (say(2.9, "gus", 1, *PLACEHOLDER), Act(FLAT, SOB)),
    (first(4.5, "vera", 2, "Blue marble below.", *PLACEHOLDER), Act(READ, CRY)),
    (part(5.9, "vera", 2, 3, "Data streams in silent grace.", *PLACEHOLDER), Act(READ, CRY)),
    (part(7.5, "desk", 2, 8, "Starlight feeds my core.", *PLACEHOLDER), Act(READ, CRY)),
    (hold(8.7, "gus", "", *PLACEHOLDER, "sob"), Act(FLAT, Pose("weep", "gape", "chest", 3.0))),
    (say(10.5, "gus", 3, *PLACEHOLDER), Act(FLAT, SOB)),
    (say(11.75, "vera", 4, *PLACEHOLDER), Act(READ, CRY)),
    (say(14.55, "desk", 5, *PLACEHOLDER), Act(Pose("side", "flat"), Pose("weep", "talk", "up", -4.0))),
    (say(17.7, "vera", 6, *PLACEHOLDER), Act(READ, CRY)),
    (say(19.8, "gus", 7, *PLACEHOLDER), Act(FLAT, Pose("wide", "talk", "point", 5.0))),
    (first(22.15, "desk", 8, "Co-host in tears now.", *PLACEHOLDER), Act(Pose("over", "talk", head=3.0), CRY)),
    (part(23.6, "desk", 8, 4, "The satellite feels nothing.", *PLACEHOLDER), Act(Pose("over", "talk", head=3.0), CRY)),
    (part(25.1, "desk", 8, 8, "Back after the break.", *PLACEHOLDER), Act(Pose("level", "talk"), CRY)),
    (hold(26.4, "vera", "", *PLACEHOLDER, "signed"), Act(Pose("level", "smirk"), CRY)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST)
EVENTS = ("card", "sob", "signed")
POST = InstagramPost(
    title="Could a satellite's haiku make you cry?",
    description=f"Parody desk, real story.\n{SOURCE.outlet}, {SOURCE.date}: {SOURCE.headline}",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#google", "#space", "#haiku", "#satellites"),
    thumbnail=Thumbnail(
        "The satellite\nwrote a haiku.", 3.8, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"
    ),
)
STORY = Story(SOURCE, TICKER, LOWERS, ACTS, EVENTS, POST, small=1)


def validate(sk: Sketch = SKETCH) -> None:
    """The story's checks."""
    STORY.validate(sk)


def overlay(cv, parent, beats, end, measure) -> None:
    """The story's words over the picture."""
    STORY.overlay(cv, parent, beats, end, measure)


def chimes(beats) -> list[float]:
    """One soft note on each of the six lines of verse, hers and the satellite's."""
    return [b.start for b in beats if b.line in (2, 8)]


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening and on her signature, a whoosh on the card, a chime on every line of verse."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    signed = sketch.events(beats, "signed")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0, signed], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05], end, seed=seed)
    chime = synth.write_tones(audio / "chime.wav", chimes(beats), end, ((1318.5, 420.0, 0.1),))
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("chime", 0.0, -12.0, root, chime),
    ]
