"""Password Expired — the sketch as data: Bruno's password expires again. Pip at the IT desk rejects his new one:
too similar to the old one. He changed every letter (his laptop says otherwise). How does IT know his old one?
They keep them all, in a spreadsheet. Was the spreadsheet password protected? It was. It expired.

Two voices (ElevenLabs premade Bill as Bruno, Alice as Pip), one shot per speaker: Bruno at his desk with his
phone's toasts and the passwords he wrote on notes on his laptop (HONEY1 to HONEY4); Pip in the meeting room,
where the board says SECURITY WEEK until it shows the spreadsheet (``board:`` events, in Pip's shot). ``SKETCH``
is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress`
draws each shot's set and props (``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon, toon_props
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1313
SLUG = "password-expired"
TITLE = "Password Expired — Bruno and Pip (Toon)"
DESCRIPTION = (
    "A Toon sketch: Bruno's password expired again, and IT rejects the new one as too similar to the old one. "
    "How does IT know his old one? They keep them all in a spreadsheet. It was password protected. It expired."
)
ACCESSIBILITY = (
    "A cartoon bear at his laptop calls a cartoon rabbit in a meeting room. Sticky notes on his laptop read HONEY1 "
    "to HONEY4; his phone shows Password expired. The board behind her says SECURITY WEEK, then PASSWORDS.XLSX. "
    "Their lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Bill (Bruno) and Alice (Pip); synthesised keyboard, buzz and sting."
NOTE = "ElevenLabs premade voices Bill and Alice at their natural pace; no reference-voice cloning."
BRUNO = Speaker(
    "bruno",
    Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.30),
    "bear",
)
PIP = Speaker(
    "pip",
    Voice(role="pip", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.50),
    "rabbit",
)
TINTS = {"bruno": "#f1dcc4", "pip": "#fbd3e0"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"bear": "IT helpdesk", "rabbit": "Bruno calling"}
TOASTS = (("IT", "Password expired."), ("IT", "Expired again."))
NOTES = ("HONEY1", "HONEY2", "HONEY3", "HONEY4")
FIRST_BOARD = "SECURITY WEEK!"
BOARD_SIZE = 44
CLOCK_START = "09:12"
END = 28.0

LINES = (
    Line("bruno", "Why does my password expire every month?"),
    Line("pip", "Security. Pick a new one."),
    Line("bruno", "Fine. Done."),
    Line("pip", "Rejected. It's too similar to your old one."),
    Line("bruno", "I changed every letter."),
    Line("pip", "Still too similar."),
    Line("bruno", "Wait. How do you know my old one?"),
    Line("pip", "We keep them all. In a spreadsheet."),
    Line("bruno", "Is the spreadsheet password protected?"),
    Line("pip", "It was. It expired."),
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
    first(0.0, "bear", 0, "Why does my password", "narrow", "flat", "type", "toast:0"),  # the hook, the toast
    part(1.2, "bear", 0, 4, "expire every month?", "wide", "open", "desk"),
    say(2.4, "rabbit", 1, "half", "smirk", "lean"),
    say(4.0, "bear", 2, "half", "flat", "type"),
    first(5.2, "rabbit", 3, "Rejected.", "narrow", "flat", "crossed"),
    part(6.0, "rabbit", 3, 1, "It's too similar to your old one.", "half", "smirk", "crossed"),
    say(7.6, "bear", 4, "wide", "open", "desk"),  # the notes on his laptop say he changed one digit
    say(9.0, "rabbit", 5, "half", "flat", "crossed"),
    first(10.4, "bear", 6, "Wait.", "narrow", "flat", "desk"),
    part(11.0, "bear", 6, 1, "How do you know my old one?", "narrow", "o", "desk"),
    hold(12.6, "rabbit", "How do you know my old one?", "side", "flat", "crossed"),  # she freezes
    say(13.8, "rabbit", 7, "half", "grin", "lean", "board:PASSWORDS.XLSX"),  # the board shows it
    hold(16.0, "bear", LINES[7].text, "shock", "drop", "face2"),
    first(17.2, "bear", 8, "Is the spreadsheet", "narrow", "flat", "desk"),
    part(18.2, "bear", 8, 3, "password protected?", "half", "o", "desk"),
    hold(19.4, "rabbit", "password protected?", "up", "flat", "crossed"),  # the hold before the punchline
    hold(20.8, "rabbit", "", "closed", "none", "crossed"),
    say(21.8, "rabbit", 9, "half", "smirk", "lean"),  # the punchline
    hold(24.0, "bear", "", "closed", "none", "face", "hangup"),  # the sting
    hold(25.6, "bear", "", "narrow", "flat", "type", "toast:1"),  # the button: his own expires again
)
SKETCH = Sketch(SLUG, TITLE, (BRUNO, PIP), LINES, BEATS, END)


def boards(beats) -> list[tuple[float, str]]:
    """The board behind Pip through the sketch: the first text from 0, then every ``board:`` event."""
    return [(0.0, FIRST_BOARD)] + sketch.events(beats, "board")


def spans(changes: list[tuple[float, str]], start: float, end: float) -> list[tuple[float, float, str]]:
    """What ``changes`` show between ``start`` and ``end``, each until the next one."""
    ends = [at for at, _ in changes[1:]] + [end]
    return [
        (max(a, start), min(b, end), text) for (a, text), b in zip(changes, ends, strict=True) if a < end and b > start
    ]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and buzz
    in Bruno's shot (his phone), board texts change in Pip's shot (the board is behind her) and fit it; exactly
    one hangup; no other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if who_at[at] != "bear":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: the phone is in Bruno's shot")
    for at, text in sketch.events(sk.beats, "board"):
        if who_at[at] != "rabbit":
            raise sketch.SketchError(f"the board at {at} s changes off screen: it is in Pip's shot")
        if not 0 < len(text) <= 40:
            raise sketch.SketchError(f"the board text {text!r} at {at} s does not fit")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the sting plays exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"toast", "board", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Bruno's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Bruno's shots: the room, the clock, the mug, his passwords on notes and his phone's toasts; Pip's: the
    meeting room and the board, swapped when it changes. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "bear":
        toon.room(cv, shot.back)
        toon_props.clock(cv, shot.back, [(0.0, CLOCK_START)])
        toon_props.mug(cv, shot.front, steam=[(app.start, app.end)])
        toon_props.notes(cv, shot.front, NOTES)
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts)
    else:
        toon_props.meeting(cv, shot.back)
        for a, b, text in spans(boards(shot.beats), app.start, app.end):
            toon_props.board_text(cv, shot.back, text, size=BOARD_SIZE, start=a, end=b)
    shot.badges(BADGES)
