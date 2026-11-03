"""Same Way — an episode of News Compiler, the parody desk, main trigger recognition: the sketch as data.

Fictional, and tagged PARODY on every frame. Two men meet in a corridor and step the same way, over and over, and every
way out is taken by both: one says sorry, so does the other; one stops, so does the other. Gus calls it as sport. Vera
reads it flat. They pass at last, and one of them has forgotten his phone.

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

SEED = 3167
SLUG = "same-way"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Same Way — News Compiler"
DESCRIPTION = (
    "A two-anchor parody news show covers two men who met in a corridor and keep stepping the same way, called like a "
    "match by one anchor and read flat by the other."
)
ACCESSIBILITY = (
    "Two cartoon news anchors at a desk, a banner across the desk and a PARODY tag in the corner. Vera, older with a "
    "silver bob and half-moon glasses, reports that two men have met in a corridor. A map from above shows them as two "
    "plain dots stepping left and right together, with a count of sidesteps. Gus, with brown curls and an orange "
    "jacket, shouts at them to stop. One says sorry and so does the other; one stops and so does the other. The dots "
    "sit still while Vera says they are laughing and neither means it. They pass, and Gus cheers. Vera says one has "
    "forgotten his phone. Gus says no, very quietly. She says he is turning around, and the dots step once more."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda and Charlie; an original sting and synthesised effects."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
TINTS = {"vera": news_kit.CREAM, "gus": news_kit.TANGERINE}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS: dict[str, int] = {}
MAP, COUNTER = "THE CORRIDOR", "SIDESTEPS"
LEFT, RIGHT = 250.0, 450.0  # the two sides of the corridor, in px of the map panel
NEAR, FAR = 440.0, 320.0  # where they stand face to face
SIDES = (LEFT, RIGHT, LEFT, RIGHT)  # the first steps, on "Left." through "to the right."
STEPPED = 0.87  # seconds between them
END_ONE, END_OTHER = 210.0, 550.0  # how far along each has got once they have passed
LAST_STEP = 0.75  # seconds into "He's turning around." at which both step once more
SMALL = -6.0  # dB: the "No." that has given up
TICKER = ("CORRIDOR: BLOCKED", "BOTH MEN: SORRY", "NEITHER MAN: MOVING", "WITNESSES: LOOKING AT THEIR SHOES")
GUS_NAME, VERA_NAME, STILL_LIVE = "GUS BELLOWS, CO-HOST", "VERA STILLMAN, ANCHOR", "DEVELOPING"
LOWERS = (  # the beat it arrives on, its kicker, its one line, and whether it slides in
    (0, STILL_LIVE, "TWO MEN, ONE CORRIDOR", True),
    (6, STILL_LIVE, "APOLOGIES EXCHANGED", True),
    (9, GUS_NAME, "CALLING THE MATCH", True),
    (10, STILL_LIVE, "BOTH MEN STOPPED", True),
    (16, GUS_NAME, "FULL TIME", True),
    (17, STILL_LIVE, "EXTRA TIME", True),
)
END = 24.3
TAIL = 0.7

FIRST_STATEMENT = ("01",)  # the take that must be finished by craft.STATEMENT_BY
LINES = (
    Line("vera", "Two men have met in a corridor."),
    Line("gus", "Going which way?"),
    Line("vera", "Left."),
    Line("gus", "Both?"),
    Line("vera", "Both. Then to the right."),
    Line("gus", "They'll sort it out."),
    Line("vera", "One has said sorry."),
    Line("gus", "Good man."),
    Line("vera", "So has the other."),
    Line("gus", "Somebody stop! Just stop!"),
    Line("vera", "One has stopped."),
    Line("gus", "Yes!"),
    Line("vera", "So has the other."),
    Line("vera", "They're laughing. Neither means it."),
    Line("vera", "They have passed."),
    Line("gus", "They did it!"),
    Line("vera", "One has forgotten his phone."),
    Line("gus", "No.", gain=SMALL),
    Line("vera", "He's turning around."),
)
PLACEHOLDER = ("side", "flat", "desk")  # a Toon pose for the sketch's check: this cast is drawn from ACTS
script = scripting.Script(LINES)
say, hold = script.say, script.hold
READ = Pose(mouth="talk")
STILL = Pose(eyes="side")
LISTEN = Pose(eyes="side", mouth="flat", arms="chest")
ROWS: tuple[tuple[sketch.Beat, Act], ...] = (
    (say(0.0, "vera", 0, *PLACEHOLDER, "first"), Act(READ, Pose("level", "flat", head=-2.0))),
    (say(1.8, "gus", 1, *PLACEHOLDER), Act(STILL, Pose("squint", "talk", "chest", -4.0))),
    (say(2.72, "phone", 2, *PLACEHOLDER, "left"), Act(READ, LISTEN)),
    (say(3.39, "phone", 3, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "chest"))),
    (say(4.04, "phone", 4, *PLACEHOLDER, "right"), Act(READ, LISTEN)),
    (say(5.58, "phone", 5, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "chest"))),
    (say(6.68, "vera", 6, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(8.0, "gus", 7, *PLACEHOLDER), Act(STILL, Pose("level", "talk", "up", 3.0))),
    (say(8.8, "vera", 8, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(9.95, "gus", 9, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", 5.0))),
    (say(11.37, "vera", 10, *PLACEHOLDER), Act(READ, LISTEN)),
    (say(12.42, "gus", 11, *PLACEHOLDER), Act(STILL, Pose("wide", "talk", "up", -4.0))),
    (say(13.12, "vera", 12, *PLACEHOLDER), Act(READ, Pose("wide", "flat", "up"))),
    (say(14.37, "phone", 13, *PLACEHOLDER, "laugh"), Act(READ, LISTEN)),
    (hold(16.17, "phone", "", *PLACEHOLDER, "dots"), Act(STILL, LISTEN)),
    (say(17.67, "phone", 14, *PLACEHOLDER, "pass"), Act(READ, LISTEN)),
    (say(18.77, "gus", 15, *PLACEHOLDER), Act(STILL, Pose("weep", "talk", "up", 4.0))),
    (say(20.12, "phone", 16, *PLACEHOLDER, "phone"), Act(READ, LISTEN)),
    (say(21.72, "phone", 17, *PLACEHOLDER), Act(STILL, Pose("side", "talk", "rest"))),
    (say(22.52, "phone", 18, *PLACEHOLDER, "turn"), Act(READ, LISTEN)),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = tuple(row[1] for row in ROWS)
SKETCH = Sketch(SLUG, TITLE, (news_kit.VERA, news_kit.GUS), LINES, BEATS, END, cast=news_kit.NEWS_CAST, tail=TAIL)
EVENTS = ("first", "left", "right", "laugh", "dots", "pass", "phone", "turn")
FACES = ((78.0, 565.0, 370.0, 320.0), (540.0, 565.0, 380.0, 320.0))  # both heads, hair included, when the desk is up
POST = InstagramPost(
    title="Have you ever done the corridor dance with a stranger?",
    description="Parody.",
    credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
    hashtags=("#parodynews", "#awkward", "#everydaylife", "#relatable"),
    thumbnail=Thumbnail("Both went left.", 3.6, "News Compiler", focus=(540.0, 860.0), zoom=1.0, place="bottom"),
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
        COUNTER,
        POST.title,
        POST.description,
    ):
        news_kit.check_copy(text)


def windows(beats, end: float) -> tuple[tuple[float, float], ...]:
    """When the corridor is up: the first steps, the laugh and the pass, and from the phone to the last frame."""
    at = {name: sketch.events(beats, name)[0][0] for name in ("left", "laugh", "phone")}
    after = {b.start: n for b, n in zip(beats, beats[1:], strict=False)}
    first = next(b.start for b in beats if b.start > at["left"] and b.who != "phone")
    passed = sketch.events(beats, "pass")[0][0]
    return ((at["left"], first), (at["laugh"], after[passed].start), (at["phone"], end))


def steps(beats) -> tuple[float, ...]:
    """The seconds both men step together in the first window, the last just after "right.": as far apart as a count
    must stay up to be read, so the tally moves with them."""
    left = sketch.events(beats, "left")[0][0] + 0.15
    return tuple(left + i * STEPPED for i in range(len(SIDES)))


def overlay(cv, parent, beats, end, measure) -> None:
    """Everything over the picture: the PARODY tag from frame 1, the banner and ticker throughout, the lower-thirds
    except under the corridor, and the corridor three times over."""
    news_inked.sign(cv, parent)
    news_inked.ticker(cv, parent, TICKER, 0.0, end, measure)
    news_inked.banner(cv, parent, 0.0, end, measure)
    spans = windows(beats, end)
    starts = [beats[row[0]].start for row in LOWERS]
    number = 0
    for a, b, (_, kicker, line, slide) in zip(starts, [*starts[1:], end], LOWERS, strict=True):
        for left, right in clipped(a, b, spans):
            news_inked.lower_third(
                cv, parent, kicker, line, left, right, measure, id=f"news-lower-{number}", slide=slide
            )
            number += 1
    (a0, b0), (a1, b1), (a2, b2) = spans
    times = steps(beats)
    one = ((a0, RIGHT, NEAR), *((t, x, NEAR) for t, x in zip(times, SIDES, strict=True)))
    other = ((a0, RIGHT, FAR), *((t, x, FAR) for t, x in zip(times, SIDES, strict=True)))
    counts = ((a0, "1"), *((t + 0.05, str(i + 2)) for i, t in enumerate(times[1:])))
    news_inked.corridor_map(cv, parent, MAP, COUNTER, one, other, counts, a0, b0, measure)
    passing = sketch.events(beats, "pass")[0][0]
    one = ((a1, RIGHT, NEAR), (passing, LEFT, NEAR), (passing + 0.3, LEFT, END_ONE))
    other = ((a1, RIGHT, FAR), (passing + 0.3, RIGHT, END_OTHER))
    news_inked.corridor_map(
        cv, parent, MAP, COUNTER, one, other, ((a1, "14"),), a1, b1, measure, id="news-corridor-map-2"
    )
    turn = sketch.events(beats, "turn")[0][0]
    back = NEAR - 20.0
    last = turn + LAST_STEP
    one = ((a2, LEFT, END_ONE), (turn, LEFT, back), (last, RIGHT, back))
    other = ((a2, RIGHT, END_OTHER), (last, LEFT, END_OTHER))
    counts = ((a2, "14"), (last + 0.05, "15"))
    news_inked.corridor_map(cv, parent, MAP, COUNTER, one, other, counts, a2, b2, measure, id="news-corridor-map-3")
    news_inked.bug(cv, parent, 0.0, end, measure)
    news_inked.parody_tag(cv, parent, 0.0, end, measure)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The sting on the opening, a whoosh on the first map, a tick on every sidestep and on the last one. Nothing under
    the held dots, and nothing after the last step."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    left = sketch.events(beats, "left")[0][0]
    turn = sketch.events(beats, "turn")[0][0]
    sting = news_kit.write_sting(audio / "sting.wav", [0.0], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [0.05, left], end, seed=seed)
    tick = news_kit.write_tick(audio / "tick.wav", [*steps(beats), turn + LAST_STEP], end)
    return [
        sketch.effect("sting", 0.0, -12.0, root, sting),
        sketch.effect("whoosh", 0.0, -14.0, root, whoosh),
        sketch.effect("tick", 0.0, -8.0, root, tick),
    ]
