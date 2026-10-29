"""Friday Sync — the sketch as data: Bruno booked a quick sync for Friday evening. It's nothing bad: he just needs
Pip to train the new hire. Then a job alert lands on her screen: her own job, for less money. It's a similar job,
says Bruno, a different vibe. Can she apply for it? Sorry: she's overqualified.

Two voices (ElevenLabs premade Alice as Pip, Bill as Bruno), one shot per speaker: Pip at her desk at the end of
the week, the clock behind her and the job alerts on her screen (toasts, in her shot); Bruno in the meeting room,
the board behind him already welcoming the new hire. ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`dress` draws each shot's set and props
(``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import scripting, sketch, toon, toon_props
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1315
SLUG = "friday-sync"
TITLE = "Friday Sync — Pip and Bruno (Toon)"
DESCRIPTION = (
    "A Toon sketch: a quick sync on Friday evening. It's nothing bad, Bruno just needs Pip to train the new hire. "
    "Then a job alert: her own job, for less money. Can she apply for it? Sorry. She's overqualified."
)
ACCESSIBILITY = (
    "A cartoon rabbit at her laptop on a Friday evening calls a cartoon bear in a meeting room whose board says "
    "WELCOME, NEW HIRE!. Her screen shows a job alert: Your job, 30% less pay, and later: Applications closed. "
    "Their lines appear in tinted pills and their mouths move with their words."
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
BADGES = {"rabbit": "Quick sync · Bruno", "bear": "Quick sync · Pip"}
TOASTS = (("Job alert", "Your job, 30% less pay."), ("Job alert", "Applications closed."))
NOTES = ("FRI", "5PM", "QUICK", "SYNC?")
BOARD = "WELCOME, NEW HIRE!"
BOARD_SIZE = 56
CLOCK_START = "16:58"
END = 29.0

LINES = (
    Line("pip", "Why is there a meeting on Friday evening?"),
    Line("bruno", "It's nothing bad. Relax."),
    Line("pip", "Nobody books Friday evening for good news."),
    Line("bruno", "I just need you to train someone."),
    Line("pip", "Train who?"),
    Line("bruno", "The new hire. Starts Monday."),
    Line("pip", "Bruno. That's my job. For less money."),
    Line("bruno", "Similar job. Different vibe."),
    Line("pip", "Can I apply for it?"),
    Line("bruno", "Sorry. You're overqualified."),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    first(0.0, "rabbit", 0, "Why is there a meeting", "narrow", "flat", "desk"),  # the hook, the invite
    part(1.3, "rabbit", 0, 5, "on Friday evening?", "narrow", "o", "crossed"),
    say(2.4, "bear", 1, "closed", "smirk", "lean"),
    first(3.8, "rabbit", 2, "Nobody books Friday evening", "half", "flat", "crossed"),
    part(5.0, "rabbit", 2, 4, "for good news.", "narrow", "smirk", "crossed"),
    say(6.0, "bear", 3, "side", "flat", "desk"),
    say(7.8, "rabbit", 4, "narrow", "o", "desk"),
    say(8.8, "bear", 5, "wide", "grin", "lean"),
    hold(10.4, "rabbit", LINES[5].text, "side", "flat", "type", "toast:0"),  # her screen buzzes
    hold(11.6, "rabbit", "", "shock", "drop", "face2"),  # she reads it
    first(12.8, "rabbit", 6, "Bruno. That's my job.", "narrow", "flat", "crossed"),
    part(14.0, "rabbit", 6, 4, "For less money.", "narrow", "drop", "crossed"),
    say(15.0, "bear", 7, "closed", "smirk", "lean"),
    say(16.6, "rabbit", 8, "wide", "grin", "lean"),
    hold(17.8, "bear", LINES[8].text, "side", "flat", "crossed"),  # the hold before the punchline
    hold(19.0, "bear", "", "half", "none", "crossed"),
    say(20.2, "bear", 9, "half", "smirk", "desk"),  # the punchline
    hold(22.0, "rabbit", "", "closed", "none", "face", "hangup"),  # the sting
    hold(23.6, "rabbit", "", "narrow", "flat", "sigh", "toast:1"),  # the button: the door closes on her
    hold(25.4, "rabbit", "", "down", "flat", "type", "clock:17:31"),  # and she starts the handover
)
SKETCH = Sketch(SLUG, TITLE, (PIP, BRUNO), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and buzz
    in Pip's shot (her screen); the clock moves forward in Pip's shot (it is behind her); exactly one hangup; no
    other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if who_at[at] != "rabbit":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: the alerts are on Pip's screen")
    for at, _ in sketch.events(sk.beats, "clock"):
        if who_at[at] != "rabbit":
            raise sketch.SketchError(f"the clock at {at} s moves off screen: it hangs in Pip's shot")
    times = [CLOCK_START] + [arg for _, arg in sketch.events(sk.beats, "clock")]
    angles = [toon_props.clock_angles(time) for time in times]
    if any(b <= a for a, b in zip(angles, angles[1:], strict=False)):
        raise sketch.SketchError(f"the clock runs backwards: {times}")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    scripting.only_events(sk.beats, {"toast", "clock", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Pip's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Pip's shots: the room, the clock, the mug, the invite on her notes and the job alerts; Bruno's: the meeting
    room with the welcome on the board. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "rabbit":
        toon.room(cv, shot.back)
        toon_props.clock(cv, shot.back, [(0.0, CLOCK_START)] + sketch.events(shot.beats, "clock"))
        toon_props.mug(cv, shot.front)
        toon_props.notes(cv, shot.front, NOTES)
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts)
    else:
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD, size=BOARD_SIZE)
    shot.badges(BADGES)
