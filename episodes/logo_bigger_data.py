"""Logo Bigger — the sketch as data: a client on speaker wants the logo bigger. Then bigger. Then it should pop.
Then smaller. That one pops. Rex sends the invoice.

Three voices (ElevenLabs premade George as the client, heard on Fern's speaker; Matilda as Fern; Charlie as
Rex), two shots: Fern in the meeting room, where the logo on the whiteboard grows with every request, and Rex at
the survey desk, typing. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what
the events ask of the logo; :func:`dress` draws each shot's set and props (``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from srstudio import scripting, sketch, toon, toon_props
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1031
SLUG = "logo-bigger"
TITLE = "Logo Bigger — Fern, Rex and the client (Toon)"
DESCRIPTION = (
    "A Toon sketch: a client on speaker wants the logo bigger, then bigger, then the size of the building, then "
    "popping, then smaller; the original pops. Rex sends the invoice."
)
ACCESSIBILITY = (
    "A cartoon frog in a meeting room takes a client's requests on speaker while the sun logo on the whiteboard "
    "grows past the board; a cartoon dog at a laptop makes the changes. Lines appear in tinted pills."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices George (the client), Matilda (Fern) and Charlie (Rex); "
    "synthesised keyboard and sting."
)
NOTE = "ElevenLabs premade voices George, Matilda and Charlie at their natural pace; no reference-voice cloning."
CLIENT = Speaker(
    "client",
    Voice(role="client", id="JBFqnCBsd6RMkjVDRZzb", name="George"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.30),
)
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.40),
    "frog",
)
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "dog",
)
TINTS = {"rex": "#ffe3b3", "fern": "#d6f5dc", "client": "#e6e6f0"}
BADGES = {"frog": "Client on speaker"}
BOARD = "LOGO v1"
END = 41.8

LINES = (
    Line("client", "Can you make the logo bigger?"),
    Line("fern", "Rex?"),
    Line("rex", "Bigger. Sure."),
    Line("client", "Bigger, please."),
    Line("client", "A bit bigger."),
    Line("fern", "It's... the size of the whiteboard."),
    Line("client", "Bigger than that."),
    Line("fern", "It is now the size of the building."),
    Line("client", "Perfect. Now make it pop."),
    Line("rex", "Pop. Sure."),
    Line("client", "Hmm. Can we see it smaller?"),
    Line("client", "That's it. That one pops."),
    Line("rex", "That's the original."),
    Line("client", "No. This one pops."),
    Line("rex", "Invoice sent."),
    Line("client", "Can you make the invoice smaller?"),
    Line("rex", "No."),
)


SCRIPT = scripting.Script(LINES)
say, hold = SCRIPT.say, SCRIPT.hold


BEATS = (
    say(0.0, "frog", 0, "wide", "flat", "desk"),  # the hook: the client's question
    say(2.2, "frog", 1, "side", "o", "lean"),
    say(3.2, "dog", 2, "half", "flat", "type"),
    hold(4.8, "frog", "", "wide", "flat", "desk", "logo:1.6"),  # the gag, shown: it grows
    say(6.0, "frog", 3, "half", "flat", "desk"),
    hold(7.2, "dog", "", "half", "flat", "type"),
    hold(8.3, "frog", "", "wide", "o", "desk", "logo:2.3"),
    say(9.5, "frog", 4, "narrow", "flat", "desk"),
    say(10.6, "frog", 5, "side", "wave", "crossed"),
    say(12.8, "frog", 6, "closed", "flat", "desk"),
    hold(14.0, "dog", "", "down", "flat", "type"),
    hold(15.1, "frog", "", "shock", "drop", "desk", "logo:4.6"),  # past the board, past the room
    say(16.3, "frog", 7, "shock", "open", "desk"),
    say(18.6, "frog", 8, "half", "flat", "face2"),
    say(20.6, "dog", 9, "half", "flat", "type", "pop"),  # a drop shadow: it pops
    hold(22.0, "frog", "", "narrow", "flat", "crossed"),
    say(23.0, "frog", 10, "wide", "o", "desk"),
    hold(25.0, "dog", "", "side", "smirk", "type"),
    hold(26.0, "frog", "", "wide", "flat", "desk", "logo:1.0"),  # the turn: back to the original
    say(27.2, "frog", 11, "half", "flat", "desk"),
    say(29.2, "dog", 12, "half", "flat", "crossed"),
    say(30.8, "frog", 13, "closed", "none", "face"),
    hold(32.6, "dog", "", "half", "flat", "desk"),
    say(33.6, "dog", 14, "half", "smirk", "type"),
    say(35.2, "frog", 15, "shock", "drop", "desk"),
    hold(37.4, "dog", "", "narrow", "flat", "desk"),  # the hold before the button
    say(38.8, "dog", 16, "narrow", "o", "desk"),
    hold(39.8, "frog", "", "half", "smirk", "crossed", "hangup"),  # the sting; the badge reads Call ended
)
SKETCH = Sketch(SLUG, TITLE, (CLIENT, FERN, REX), LINES, BEATS, END)


def logo_sizes(beats) -> list[tuple[float, float]]:
    """``(project second, scale)`` for :func:`srstudio.toon_props.logo`: the original from 0, then every event."""
    return [(0.0, 1.0)] + [(at, float(arg)) for at, arg in sketch.events(beats, "logo")]


def shadow_span(beats, end: float) -> tuple[float, float] | None:
    """From the ``pop`` event to the next change of size (the original does not pop), or the end."""
    pops = sketch.events(beats, "pop")
    if not pops:
        return None
    start = pops[0][0]
    later = [at for at, _ in sketch.events(beats, "logo") if at > start]
    return (start, later[0] if later else end)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: logo sizes are positive numbers
    the logo can ramp between, shown on Fern's shots; one pop before a return to the original; one hangup."""
    sketch.check(sk)
    try:
        sizes = logo_sizes(sk.beats)
    except ValueError:
        raise sketch.SketchError("logo events take a number: logo:1.6") from None
    toon_props.scale_keys(sizes)
    for at, _ in sketch.events(sk.beats, "logo"):
        if next(b for b in sk.beats if b.start == at).who != "frog":
            raise sketch.SketchError(f"the logo changes at {at} s off screen: it hangs in Fern's room")
    if len(sketch.events(sk.beats, "pop")) != 1 or shadow_span(sk.beats, sk.end) is None:
        raise sketch.SketchError("the logo pops exactly once")
    scripting.exactly_once(sk.beats, "hangup", "the call ends exactly once")
    scripting.only_events(sk.beats, {"logo", "pop", "hangup"})


def dress(shot) -> None:
    """Fern's shots: the meeting room, the board's label and the logo at its asked sizes behind her, the speaker
    badge in front; Rex's: the room."""
    cv, app = shot.cv, shot.app
    if app.who == "frog":
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD)
        toon_props.logo(cv, shot.back, logo_sizes(shot.beats), shadow=shadow_span(shot.beats, shot.end))
    else:
        toon.room(cv, shot.back)
    shot.badges(BADGES)
