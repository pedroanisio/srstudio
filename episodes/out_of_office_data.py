"""Out of Office — the sketch as data: Pip calls Bruno, who is on vacation. His out-of-office is on, and he has
answered every email to say so, personally, because it is warmer. The calendar behind him tears through the week
while they talk. His vacation ends tomorrow, and everyone knows he rested: even his boss replied. From her
vacation. Then his own auto-reply arrives.

Two voices (ElevenLabs premade Alice as Pip, Bill as Bruno, as in *Quick Question*), one shot per speaker: Bruno at
home at night with the tear-off calendar, the desk lamp and the plant, his phone's toasts in front; Pip in the
meeting room with the quarter's plan on the board. ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`dress` draws each shot's set and props
(``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon_props, toon_sets
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1072
SLUG = "out-of-office"
TITLE = "Out of Office — Pip and Bruno (Toon)"
DESCRIPTION = (
    "A Toon sketch: Bruno is on vacation, out-of-office on. He has answered every email to say so, personally. "
    "The calendar tears through the week. His boss replies too, from her vacation."
)
ACCESSIBILITY = (
    "A cartoon rabbit in a meeting room calls a cartoon bear at his desk at home at night. Behind him a tear-off "
    "calendar loses a page at a time, a desk lamp lights his laptop and a plant sways. Notifications slide onto his "
    "phone. Their lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno); synthesised keyboard, buzz and sting."
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
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"bear": "Pip calling", "rabbit": "Bruno on the line"}
BOARD = "Q4 PLAN"
FIRST_PAGE = "OCT 27"
TOASTS = (("Dana", "Enjoy your time off!"), ("Bruno", "Auto-reply: I'm away."))
PLANT_AT = (470, 838)  # right of the laptop, clear of his paws and the cactus
TOAST_SIZE = 34  # the toasts carry the boss's reply and the button: read on a phone
END = 31.0

LINES = (
    Line("pip", "Aren't you on vacation?"),
    Line("bruno", "Yep. Out of office is on."),
    Line("pip", "You replied to every email."),
    Line("bruno", "To say I'm out of office."),
    Line("pip", "Personally? All of them?"),
    Line("bruno", "It's warmer."),
    Line("pip", "Your vacation ends tomorrow."),
    Line("bruno", "And everyone knows I rested."),
    Line("pip", "Even Dana replied?"),
    Line("bruno", "From her vacation."),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "rabbit", 0, "narrow", "flat", "crossed"),  # the hook: the question
    say(2.0, "bear", 1, "half", "grin", "type"),
    say(3.8, "rabbit", 2, "narrow", "flat", "desk"),
    say(5.6, "bear", 3, "closed", "smirk", "type"),
    say(7.4, "rabbit", 4, "shock", "o", "face2"),
    say(9.2, "bear", 5, "half", "grin", "lean"),
    hold(10.4, "bear", "", "half", "none", "type", "page:OCT 29"),  # the week tears away while he types
    hold(11.6, "bear", "", "half", "none", "type", "page:NOV 1"),
    say(12.8, "rabbit", 6, "half", "flat", "sigh"),
    say(14.8, "bear", 7, "wide", "grin", "lean"),
    hold(16.6, "bear", LINES[7].text, "down", "o", "desk", "toast:0"),  # the boss replies
    say(17.8, "rabbit", 8, "wide", "open", "lean"),
    hold(19.6, "bear", LINES[8].text, "side", "flat", "desk"),  # the hold before the punchline
    hold(20.6, "bear", LINES[8].text, "half", "none", "crossed"),
    say(21.8, "bear", 9, "half", "smirk", "lean"),  # the punchline
    hold(23.6, "rabbit", "", "closed", "none", "face", "hangup"),  # the sting
    hold(25.2, "bear", "", "half", "flat", "type", "toast:1"),  # the button: his own auto-reply
    hold(27.0, "bear", "", "closed", "grin", "lean"),
)
SKETCH = Sketch(SLUG, TITLE, (PIP, BRUNO), LINES, BEATS, END)


def pages(beats) -> list[tuple[float, str]]:
    """The calendar through the sketch: the first page from 0, then every ``page:`` event."""
    return [(0.0, FIRST_PAGE)] + sketch.events(beats, "page")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the calendar's pages parse and
    rise, and tear in Bruno's shots, where it hangs; toasts index ``TOASTS`` and buzz on Bruno's phone; exactly
    one hangup; no other events."""
    sketch.check(sk)
    try:
        toon_sets.parse_pages(pages(sk.beats))
    except toon_sets.ToonDataError as error:
        raise sketch.SketchError(f"the calendar: {error}") from error
    for kind in ("page", "toast"):
        for at, _ in sketch.events(sk.beats, kind):
            if next(b for b in sk.beats if b.start == at).who != "bear":
                raise sketch.SketchError(f"the {kind} at {at} s is off screen: it is in Bruno's shot")
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the call ends exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"page", "toast", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Bruno's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for i, (at, idx) in enumerate(arrivals):
        nxt = arrivals[i + 1][0] if i + 1 < len(arrivals) else app.end
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, nxt, sender, text))
    return out


def dress(shot) -> None:
    """Bruno's shots: home at night, the calendar where the clock hangs, the plant and the lamp lit over the
    laptop, his phone's toasts in front; Pip's: the meeting room with the plan on the board. Both carry the call
    badge."""
    cv, app = shot.cv, shot.app
    if app.who == "bear":
        toon_sets.home(cv, shot.back, end=shot.end)
        toon_sets.calendar(cv, shot.back, pages(shot.beats))
        toon_sets.desk_lamp(cv, shot.front)
        toon_sets.plant(cv, shot.front, at=PLANT_AT, scale=0.7, end=shot.end)  # in front of the lamp's glow
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts, size=TOAST_SIZE)
    else:
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD, size=56)
    shot.badges(BADGES)
