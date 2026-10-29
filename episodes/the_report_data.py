"""The Report — the sketch as data: Fern calls Rex about the report he asked her to remind him of. He has never
heard of it. The reminders he sent, the notes on his laptop and the one on his forehead have.

Two voices (ElevenLabs premade Charlie as Rex, Matilda as Fern), one shot per speaker: Rex at the survey desk
with the sticky notes, the clock and his phone buzzing his own messages in; Fern in the meeting room with the
review on the board. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the
events ask of the props; :func:`dress` draws each shot's set and props (``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from srstudio import sketch, toon, toon_cast, toon_props
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1030
SLUG = "the-report"
TITLE = "The Report — Rex and Fern (Toon)"
DESCRIPTION = (
    "A Toon sketch: Fern calls Rex about the report he asked her to remind him of; Rex has never heard of any "
    "report, whatever his own messages, the notes on his laptop and the one on his forehead say."
)
ACCESSIBILITY = (
    "A cartoon dog at a laptop, a sticky note on his forehead, takes a call from a cartoon frog in a meeting room; "
    "their lines appear in tinted pills, his phone shows his own reminders, a clock passes nine."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); synthesised keyboard, phone and sting."
)
NOTE = "ElevenLabs premade voices Charlie and Matilda at their natural pace; no reference-voice cloning."
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "dog",
)
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.40),
    "frog",
)
TINTS = {"rex": "#ffe3b3", "fern": "#d6f5dc"}
BADGES = {"dog": "Fern calling", "frog": "Rex on the line"}
NOTES = ("REPORT!!", "9 AM", "DO NOT", "FORGET")
TOASTS = (("Rex", "THE REPORT. 9 AM."), ("Rex", "DO NOT LET ME FORGET."))
BOARD = "REPORT REVIEW 9:00"
CLOCK_START = "09:04"
STICKER = toon_cast.sticky_note(178, 492)  # on Rex's forehead from the first frame
END = 33.5

LINES = (
    Line("fern", "Rex, where's the report?"),
    Line("rex", "What report?"),
    Line("fern", "The report. You asked me to remind you."),
    Line("rex", "I did not."),
    Line("fern", "You sent me eleven messages."),
    Line("rex", "That wasn't me."),
    Line("fern", "Rex. They say Rex."),
    Line("rex", "Anyone can type Rex."),
    Line("fern", "You put notes on your laptop."),
    Line("rex", "Those are... decorative."),
    Line("fern", "Rex."),
    Line("rex", "Yes."),
    Line("fern", "It's on your forehead."),
    Line("rex", "...What report?"),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def part(start: float, who: str, line: int, word: int, caption: str, eyes: str, mouth: str, arms: str) -> Beat:
    """A beat on a later word of a line, captioned with that part of it (a long line in two pills)."""
    if caption not in LINES[line].text or LINES[line].text.split()[word] != caption.split()[0]:
        raise sketch.SketchError(f"{caption!r} is not line {line} from word {word}")
    return Beat(start, who, caption, eyes, mouth, arms, line, word, "")


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "dog", 0, "wide", "flat", "desk"),  # the hook: Fern's question, Rex hearing it
    say(2.0, "dog", 1, "up", "o", "desk"),
    Beat(3.4, "frog", "The report.", "narrow", "flat", "desk", 2, 0),
    part(4.5, "frog", 2, 2, "You asked me to remind you.", "narrow", "flat", "desk"),
    say(6.6, "dog", 3, "side", "flat", "crossed"),
    say(8.0, "frog", 4, "half", "wave", "lean"),
    hold(10.0, "dog", LINES[4].text, "shock", "drop", "desk", "toast:0"),
    say(11.3, "dog", 5, "side", "flat", "sigh"),
    hold(12.6, "dog", LINES[5].text, "shock", "o", "desk", "toast:1"),
    say(13.8, "frog", 6, "narrow", "flat", "crossed"),
    say(15.6, "dog", 7, "half", "smirk", "crossed"),
    say(17.6, "frog", 8, "half", "flat", "desk"),
    hold(19.6, "dog", LINES[8].text, "side", "flat", "desk", "clock:09:05"),  # he looks at the notes
    say(20.6, "dog", 9, "down", "flat", "sigh"),
    say(22.6, "frog", 10, "closed", "none", "face2"),
    say(23.8, "dog", 11, "wide", "o", "desk"),
    say(24.9, "frog", 12, "half", "flat", "crossed"),
    hold(26.6, "dog", LINES[12].text, "up", "flat", "desk"),  # the hold: he tries to see his own forehead
    hold(28.0, "dog", LINES[12].text, "up", "none", "desk"),
    say(28.6, "dog", 13, "wide", "open", "desk"),  # the punchline
    hold(30.2, "frog", "", "closed", "none", "face", "hangup"),  # the sting; the badge reads Call ended
    hold(31.4, "dog", "", "half", "flat", "type", "clock:09:06"),  # and he goes back to typing
)
SKETCH = Sketch(SLUG, TITLE, (REX, FERN), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and fall
    on Rex, clock times parse and rise, exactly one hangup."""
    sketch.check(sk)
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if next(b for b in sk.beats if b.start == at).who != "dog":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: Rex's phone is in Rex's shot")
    times = [CLOCK_START] + [arg for _, arg in sketch.events(sk.beats, "clock")]
    angles = [toon_props.clock_angles(time) for time in times]
    if any(b <= a for a, b in zip(angles, angles[1:], strict=False)):
        raise sketch.SketchError(f"the clock runs backwards: {times}")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the call ends exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"toast", "clock", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Rex's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Rex's shots: the room, the clock behind him, the mug, the notes and his phone's toasts in front; Fern's:
    the meeting room with the review on the board. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "dog":
        toon.room(cv, shot.back)
        clock = [(0.0, CLOCK_START)] + [(at, arg) for at, arg in sketch.events(shot.beats, "clock")]
        toon_props.clock(cv, shot.back, clock)
        toon_props.mug(cv, shot.front, steam=[(app.start, app.end)])
        toon_props.notes(cv, shot.front, NOTES)
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts)
    else:
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD, size=36)
    shot.badges(BADGES)
