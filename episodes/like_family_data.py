"""Like Family — the sketch as data: Fern asks Rex about her salary. We're not a company, he says, we're a family.
Then she'd like an allowance. Families don't talk about money; hers talks about nothing else. He thinks of her
like a daughter. Then she'll see him at Christmas. Let's keep this professional: the board behind him changes from
family to team. Professional, then: a raise? Sorry. She's like family.

Two voices (ElevenLabs premade Matilda as Fern, Charlie as Rex), one shot per speaker: Fern at her desk, her rent
on the notes on her laptop and the clock behind her; Rex in the meeting room, the board behind him saying WE ARE
FAMILY until it says WE ARE A TEAM, and family again when it suits him (``board:`` events, in Rex's shot).
``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props;
:func:`dress` draws each shot's set and props (``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon, toon_props
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1316
SLUG = "like-family"
TITLE = "Like Family — Fern and Rex (Toon)"
DESCRIPTION = (
    "A Toon sketch: Fern asks about her salary. We're not a company, Rex says, we're a family. Then she'd like an "
    "allowance. He thinks of her like a daughter. Then she'll see him at Christmas. So, a raise? Sorry: like family."
)
ACCESSIBILITY = (
    "A cartoon frog at her laptop, notes on it reading RENT and DUE, calls a cartoon dog in a meeting room. The "
    "board behind him says WE ARE FAMILY, then WE ARE A TEAM when she says Christmas, then family again. Their "
    "lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex); synthesised keyboard and sting."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "frog",
)
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.45),
    "dog",
)
TINTS = {"fern": "#d5f0c8", "rex": "#f6dcb8"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"frog": "Rex · 1:1", "dog": "Fern · 1:1"}
NOTES = ("RENT", "DUE", "RENT", "AGAIN")
FIRST_BOARD = "WE ARE FAMILY"
BOARD_SIZE = 60
CLOCK_START = "16:55"
END = 29.0

LINES = (
    Line("fern", "Rex, can we talk about my salary?"),
    Line("rex", "Fern. We're not a company. We're a family."),
    Line("fern", "Great. Then I'd like an allowance."),
    Line("rex", "Families don't talk about money."),
    Line("fern", "Mine does. It's all we talk about."),
    Line("rex", "Look. I think of you like a daughter."),
    Line("fern", "Then I'll see you at Christmas."),
    Line("rex", "Let's keep this professional."),
    Line("fern", "Professional. So, a raise?"),
    Line("rex", "Sorry. You're like family."),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def first(start: float, who: str, line: int, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    """The first beat of a long line, captioned with its first part."""
    if not LINES[line].text.startswith(caption):
        raise sketch.SketchError(f"{caption!r} does not start line {line}")
    return Beat(start, who, caption, eyes, mouth, arms, line, 0, event)


def part(start: float, who: str, line: int, word: int, caption: str, eyes: str, mouth: str, arms: str) -> Beat:
    """A beat on a later word of a line, captioned with that part of it (a long line in two pills)."""
    if not LINES[line].text.endswith(caption) or LINES[line].text.split()[word] != caption.split()[0]:
        raise sketch.SketchError(f"{caption!r} is not line {line} from word {word}")
    return Beat(start, who, caption, eyes, mouth, arms, line, word, "")


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "frog", 0, "half", "flat", "desk"),  # the hook: the question, the rent on her laptop
    first(2.2, "dog", 1, "Fern. We're not a company.", "closed", "smirk", "lean"),
    part(3.6, "dog", 1, 5, "We're a family.", "wide", "grin", "lean"),
    say(4.6, "frog", 2, "wide", "grin", "lean"),
    say(6.6, "dog", 3, "narrow", "flat", "crossed"),
    say(8.4, "frog", 4, "half", "smirk", "crossed"),
    say(10.4, "dog", 5, "closed", "grin", "lean"),
    say(12.6, "frog", 6, "wide", "grin", "lean"),
    hold(14.6, "dog", LINES[6].text, "shock", "drop", "desk"),  # Christmas lands
    say(15.8, "dog", 7, "narrow", "flat", "crossed", "board:WE ARE A TEAM"),  # the board changes behind him
    say(17.8, "frog", 8, "half", "smirk", "desk"),
    hold(19.6, "dog", LINES[8].text, "side", "flat", "crossed"),  # the hold before the punchline
    hold(20.8, "dog", "", "side", "none", "crossed", "board:WE ARE FAMILY!"),  # and back again
    say(22.0, "dog", 9, "closed", "grin", "lean"),  # the punchline
    hold(24.0, "frog", "", "closed", "none", "face", "hangup"),  # the sting
    hold(25.6, "frog", "", "down", "flat", "type", "clock:17:30"),  # the button: back to work, unpaid overtime
)
SKETCH = Sketch(SLUG, TITLE, (FERN, REX), LINES, BEATS, END)


def boards(beats) -> list[tuple[float, str]]:
    """The board behind Rex through the sketch: the first text from 0, then every ``board:`` event."""
    return [(0.0, FIRST_BOARD)] + sketch.events(beats, "board")


def spans(changes: list[tuple[float, str]], start: float, end: float) -> list[tuple[float, float, str]]:
    """What ``changes`` show between ``start`` and ``end``, each until the next one."""
    ends = [at for at, _ in changes[1:]] + [end]
    return [
        (max(a, start), min(b, end), text) for (a, text), b in zip(changes, ends, strict=True) if a < end and b > start
    ]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the board changes in Rex's shot
    (it is behind him) and fits; the clock moves forward in Fern's shot (it is behind her); exactly one hangup; no
    other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, text in sketch.events(sk.beats, "board"):
        if who_at[at] != "dog":
            raise sketch.SketchError(f"the board at {at} s changes off screen: it is in Rex's shot")
        if not 0 < len(text) <= 40:
            raise sketch.SketchError(f"the board text {text!r} at {at} s does not fit")
    for at, _ in sketch.events(sk.beats, "clock"):
        if who_at[at] != "frog":
            raise sketch.SketchError(f"the clock at {at} s moves off screen: it hangs in Fern's shot")
    times = [CLOCK_START] + [arg for _, arg in sketch.events(sk.beats, "clock")]
    angles = [toon_props.clock_angles(time) for time in times]
    if any(b <= a for a, b in zip(angles, angles[1:], strict=False)):
        raise sketch.SketchError(f"the clock runs backwards: {times}")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the sting plays exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"board", "clock", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def dress(shot) -> None:
    """Fern's shots: the room, the clock, the mug and the rent on her notes; Rex's: the meeting room and the
    board, swapped when it changes. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "frog":
        toon.room(cv, shot.back)
        toon_props.clock(cv, shot.back, [(0.0, CLOCK_START)] + sketch.events(shot.beats, "clock"))
        toon_props.mug(cv, shot.front, steam=[(app.start, app.end)])
        toon_props.notes(cv, shot.front, NOTES)
    else:
        toon_props.meeting(cv, shot.back)
        for a, b, text in spans(boards(shot.beats), app.start, app.end):
            toon_props.board_text(cv, shot.back, text, size=BOARD_SIZE, start=a, end=b)
    shot.badges(BADGES)
