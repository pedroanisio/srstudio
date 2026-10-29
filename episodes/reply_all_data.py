"""Reply All — the sketch as data: Bruno meant to send it to Pip. He sent it to the whole company: this meeting
could have been an email. Fair point. The CEO agrees; she has cancelled every meeting. He's a hero. Then the CEO
again: your job, also an email. Is that a promotion? It's an email.

Two voices (ElevenLabs premade Alice as Pip, Bill as Bruno), one shot per speaker: Pip at her desk late, the clock
behind her; Bruno at home at night, his phone bringing the CEO's replies (toasts, in his shot). ``SKETCH`` is
checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress`
draws each shot's set and props (``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import scripting, sketch, toon, toon_props, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1317
SLUG = "reply-all"
TITLE = "Reply All — Pip and Bruno (Toon)"
DESCRIPTION = (
    "A Toon sketch: Bruno replied all to the whole company. This meeting could have been an email. The CEO agrees "
    "and cancels every meeting. He's a hero. Then the CEO writes again: your job, also an email."
)
ACCESSIBILITY = (
    "A cartoon rabbit at her laptop late at night calls a cartoon bear at home. His phone buzzes with messages from "
    "Dana, the CEO: Agreed., then Your job: also an email. Their lines appear in tinted pills and their mouths move "
    "with their words."
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
BADGES = {"rabbit": "Bruno calling", "bear": "Pip on the line"}
TOASTS = (("Dana (CEO)", "Agreed."), ("Dana (CEO)", "Your job: also an email."))
NOTES = ("INBOX", "4,812")
CLOCK_START = "22:40"
END = 29.0

LINES = (
    Line("pip", "Bruno. Did you just reply all?"),
    Line("bruno", "No. I sent it to you."),
    Line("pip", "And to the entire company."),
    Line("bruno", "What did I write?"),
    Line("pip", "This meeting could have been an email."),
    Line("bruno", "Well. That's fair."),
    Line("bruno", "The CEO agrees!"),
    Line("pip", "She just canceled every meeting."),
    Line("bruno", "I'm a hero."),
    Line("bruno", "Is that a promotion?"),
    Line("pip", "It's an email."),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    say(0.0, "rabbit", 0, "wide", "o", "desk"),  # the hook: the question, her inbox on her laptop
    say(2.0, "bear", 1, "half", "flat", "lean"),
    say(3.4, "rabbit", 2, "narrow", "flat", "crossed"),
    say(5.0, "bear", 3, "shock", "o", "face2"),
    first(6.4, "rabbit", 4, "This meeting", "half", "flat", "type"),
    part(7.4, "rabbit", 4, 2, "could have been an email.", "narrow", "flat", "type"),
    say(8.6, "bear", 5, "side", "smirk", "crossed"),
    hold(9.8, "bear", "", "side", "none", "crossed", "toast:0"),  # his phone buzzes
    say(10.8, "bear", 6, "wide", "grin", "lean"),
    say(12.2, "rabbit", 7, "half", "flat", "sigh"),
    say(14.0, "bear", 8, "closed", "grin", "lean"),
    hold(15.4, "bear", "", "closed", "grin", "lean", "toast:1"),  # and again
    hold(16.8, "bear", "", "down", "flat", "desk"),  # he reads it
    say(18.0, "bear", 9, "wide", "grin", "lean"),
    hold(19.4, "rabbit", LINES[9].text, "half", "flat", "crossed"),  # the hold before the punchline
    hold(20.6, "rabbit", "", "closed", "none", "crossed"),
    say(21.8, "rabbit", 10, "half", "flat", "desk"),  # the punchline
    hold(23.4, "bear", "", "shock", "drop", "face", "hangup"),  # the sting
    hold(25.0, "rabbit", "", "down", "flat", "type", "clock:22:52"),  # the button: she goes back to her inbox
)
SKETCH = Sketch(SLUG, TITLE, (PIP, BRUNO), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and buzz
    in Bruno's shot (his phone); the clock moves forward in Pip's shot (it is behind her); exactly one hangup; no
    other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if who_at[at] != "bear":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: the phone is in Bruno's shot")
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
    """The toasts that arrive during one of Bruno's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Pip's shots: the room, the clock, the mug and her inbox on her notes; Bruno's: his room at night and his
    phone's toasts. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "rabbit":
        toon.room(cv, shot.back)
        toon_props.clock(cv, shot.back, [(0.0, CLOCK_START)] + sketch.events(shot.beats, "clock"))
        toon_props.mug(cv, shot.front)
        toon_props.notes(cv, shot.front, NOTES)
    else:
        toon_sets.home(cv, shot.back, end=app.end)
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts)
    shot.badges(BADGES)
