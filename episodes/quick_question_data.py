"""Quick Question — the sketch as data: Pip calls Bruno with a quick question. First, some context. It started in
March. Then Dave left. Forty-six minutes later the question is when the stand-up is. It was three minutes ago; it
is written on the board behind her. She has a quick follow-up.

Two voices (ElevenLabs premade Alice as Pip, Bill as Bruno), one shot per speaker: Bruno at the desk with the
clock behind him (it jumps while Pip explains) and his coffee going cold; Pip in the meeting room with the
stand-up time on the whiteboard from the first frame. Both characters are lip-synced to their own takes.
``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the
props; :func:`dress` draws each shot's set and props (``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon, toon_props
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1032
SLUG = "quick-question"
TITLE = "Quick Question — Pip and Bruno (Toon)"
DESCRIPTION = (
    "A Toon sketch: Pip has a quick question for Bruno. First, some context: March, then Dave. Forty-six "
    "minutes later the question is when the stand-up is. It was three minutes ago. She has a quick follow-up."
)
ACCESSIBILITY = (
    "A cartoon rabbit in a meeting room calls a cartoon bear at his laptop; the whiteboard behind her shows the "
    "stand-up time the whole time, his clock jumps from 9:02 to 9:48 and his coffee stops steaming. Their lines "
    "appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno); synthesised keyboard and sting."
NOTE = "ElevenLabs premade voices Alice and Bill at their natural pace; no reference-voice cloning."
PIP = Speaker(
    "pip",
    Voice(role="pip", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.50),
    "rabbit",
)
BRUNO = Speaker(
    "bruno",
    Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.30),
    "bear",
)
TINTS = {"pip": "#fbd3e0", "bruno": "#f1dcc4"}
# the Toon's viseme reading (12 Hz, o/u/w round) with English spelling, every b/m/p closed, a one-frame lead and
# the mouth held over short joins between words (srstudio.lipsync, ADR 0019)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"bear": "Pip calling", "rabbit": "Bruno on the line"}
NOTES = ("DEEP", "WORK", "DO NOT", "DISTURB")
BOARD = "STAND-UP 9:45"
BOARD_SIZE = 56
CLOCK_START = "09:02"
END = 32.0

LINES = (
    Line("pip", "Quick question. Got a sec?"),
    Line("bruno", "Sure. Go ahead."),
    Line("pip", "So. Some context first."),
    Line("bruno", "How much context?"),
    Line("pip", "It started in March."),
    Line("bruno", "It's October."),
    Line("pip", "Then Dave left. You remember Dave."),
    Line("bruno", "I don't remember Dave."),
    Line("pip", "Doesn't matter. So after Dave..."),
    Line("bruno", "Pip. The question."),
    Line("pip", "Right. Right. Quick question."),
    Line("pip", "When's the stand-up?"),
    Line("bruno", "Three minutes ago. It's on the board."),
    Line("pip", "Oh. Quick follow-up."),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def part(start: float, who: str, line: int, word: int, caption: str, eyes: str, mouth: str, arms: str) -> Beat:
    """A beat on a later word of a line, captioned with that part of it (a long line in two pills)."""
    if caption not in LINES[line].text or LINES[line].text.split()[word] != caption.split()[0]:
        raise sketch.SketchError(f"{caption!r} is not line {line} from word {word}")
    return Beat(start, who, caption, eyes, mouth, arms, line, word, "")


def first(start: float, who: str, line: int, caption: str, eyes: str, mouth: str, arms: str) -> Beat:
    """The first beat of a long line, captioned with its first part."""
    if not LINES[line].text.startswith(caption):
        raise sketch.SketchError(f"{caption!r} does not start line {line}")
    return Beat(start, who, caption, eyes, mouth, arms, line, 0, "")


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "rabbit", 0, "wide", "grin", "lean"),  # the hook: the question, the answer already on the board
    say(2.0, "bear", 1, "half", "flat", "type"),
    say(3.4, "rabbit", 2, "half", "flat", "desk"),
    say(5.2, "bear", 3, "narrow", "flat", "desk"),
    say(6.6, "rabbit", 4, "up", "wave", "lean"),
    say(8.4, "bear", 5, "narrow", "flat", "crossed"),
    first(9.8, "rabbit", 6, "Then Dave left.", "side", "smirk", "lean"),
    part(10.9, "rabbit", 6, 3, "You remember Dave.", "wide", "grin", "lean"),
    hold(12.0, "bear", "You remember Dave.", "half", "flat", "sigh", "clock:09:31"),  # half an hour of Dave
    say(12.8, "bear", 7, "half", "flat", "sigh"),
    say(14.4, "rabbit", 8, "wide", "open", "desk"),
    hold(16.4, "bear", LINES[8].text, "closed", "none", "face", "clock:09:48"),
    say(17.4, "bear", 9, "narrow", "flat", "desk"),
    say(18.8, "rabbit", 10, "wide", "grin", "desk"),
    say(20.6, "rabbit", 11, "up", "o", "lean"),
    hold(22.2, "bear", LINES[11].text, "shock", "drop", "desk"),  # all that, for this
    first(23.4, "bear", 12, "Three minutes ago.", "half", "flat", "desk"),
    part(24.4, "bear", 12, 3, "It's on the board.", "narrow", "flat", "crossed"),
    hold(25.4, "rabbit", "It's on the board.", "side", "flat", "desk"),  # the hold: she turns to the board
    hold(26.4, "rabbit", "", "wide", "o", "desk"),
    say(27.4, "rabbit", 13, "half", "grin", "lean"),  # the button
    hold(29.0, "bear", "", "closed", "none", "desk", "hangup"),  # the sting; the badge reads Call ended
    hold(30.2, "bear", "", "half", "flat", "type", "clock:09:52"),  # and he goes back to work
)
SKETCH = Sketch(SLUG, TITLE, (PIP, BRUNO), LINES, BEATS, END)


def cold_at(beats) -> float | None:
    """When Bruno's coffee stops steaming: at the first jump of the clock."""
    jumps = sketch.events(beats, "clock")
    return jumps[0][0] if jumps else None


def steam_spans(beats, app) -> list[tuple[float, float]]:
    """The spans of one of Bruno's shots in which the mug still steams."""
    cold = cold_at(beats)
    stop = app.end if cold is None else min(app.end, cold)
    return [(app.start, stop)] if stop > app.start else []


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: clock times parse, rise and fall
    in Bruno's shots, where the clock hangs; exactly one hangup; no other events."""
    sketch.check(sk)
    for at, _ in sketch.events(sk.beats, "clock"):
        if next(b for b in sk.beats if b.start == at).who != "bear":
            raise sketch.SketchError(f"the clock at {at} s moves off screen: it hangs in Bruno's shot")
    times = [CLOCK_START] + [arg for _, arg in sketch.events(sk.beats, "clock")]
    angles = [toon_props.clock_angles(time) for time in times]
    if any(b <= a for a, b in zip(angles, angles[1:], strict=False)):
        raise sketch.SketchError(f"the clock runs backwards: {times}")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the call ends exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"clock", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def dress(shot) -> None:
    """Bruno's shots: the room, the clock behind him, the mug (steaming until the clock jumps) and the notes on
    his laptop; Pip's: the meeting room with the stand-up time on the board. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "bear":
        toon.room(cv, shot.back)
        clock = [(0.0, CLOCK_START)] + [(at, arg) for at, arg in sketch.events(shot.beats, "clock")]
        toon_props.clock(cv, shot.back, clock)
        toon_props.mug(cv, shot.front, steam=steam_spans(shot.beats, app))
        toon_props.notes(cv, shot.front, NOTES)
    else:
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD, size=BOARD_SIZE)
    shot.badges(BADGES)
