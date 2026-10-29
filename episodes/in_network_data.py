"""In Network — the sketch as data: Gil calls his insurer about a broken arm. Dana, in claims, is delighted: which
arm? The left. Oh no, they cover the right. The hospital is in network; the doctor is not. The ambulance? Was he
awake? Then he chose it. So what does he do? Try again in January: fresh deductible. The calendar jumps to January
and a new claim comes in.

Two voices (ElevenLabs premade Chris as Gil, Jessica as Dana), one shot per speaker: Gil in the home office at night
with a tear-off calendar that jumps to January 1 at the end, Dana in a call-centre cubicle with a headset and a
CALLS WAITING board that climbs while she takes her time. The claims arrive as toasts on Gil's phone (``toast:``
events), the board's count changes on ``tick:`` events, the calendar on ``page:``. Both characters are lip-synced
to their own takes. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events
ask of the props; :func:`dress` draws each shot's set and props (``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import scripting, sketch, toon_cast, toon_props, toon_sets
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.toon import ToonDataError
from srstudio.voice import Voice, VoiceSettings

SEED = 1091
SLUG = "in-network"
TITLE = "In Network — Gil and Dana (Toon)"
DESCRIPTION = (
    "A Toon sketch on the phone: Gil asks his insurer whether a broken arm is covered. It depends which arm. The "
    "doctor is out of network, the ambulance was his choice, and the advice is to try again in January."
)
ACCESSIBILITY = (
    "A cartoon frog in a home office at night talks on the phone with a cartoon dog in a headset at a call-centre "
    "cubicle, under a board counting the calls waiting that climbs from 41 to 999. Phone notifications slide in over "
    "the frog's window: a claim received, the left arm not covered, the ambulance bill and, at the end, a second "
    "claim. The tear-off calendar behind him jumps from October to January 1. Their lines appear in tinted pills and "
    "their mouths move with their words."
)
NARRATION = (
    "Voiced with ElevenLabs premade voices Chris (Gil) and Jessica (Dana); synthesised keyboard, buzz and sting."
)
NOTE = "ElevenLabs premade voices Chris and Jessica at their natural pace; no reference-voice cloning."
GIL = Speaker(
    "gil",
    Voice(role="gil", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35),
    "frog",
)
DANA = Speaker(
    "dana",
    Voice(role="dana", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.55),
    "dog",
)
TINTS = {"gil": "#d5f0c8", "dana": "#f6dcb8"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"frog": "Dana, Claims", "dog": "Gil, member 4471"}
STICKERS = {"dog": toon_cast.headset(toon_cast.DOG)}
FIRST_PAGE = "OCT 29"
FIRST_WAITING = 41
TOASTS = (
    ("Claims", "Claim #4471 received"),
    ("Claims", "Left arm: not covered"),
    ("Claims", "Ambulance: $3,400"),
    ("Claims", "Claim #4472 received"),
)
END = 31.0

LINES = (
    Line("gil", "Hi. Is a broken arm covered?"),
    Line("dana", "Absolutely! Which arm?"),
    Line("gil", "The left one."),
    Line("dana", "Oh no. We cover the right."),
    Line("gil", "The hospital is in network!"),
    Line("dana", "The hospital is. The doctor isn't."),
    Line("gil", "And the ambulance?"),
    Line("dana", "Were you awake?"),
    Line("gil", "Yes?"),
    Line("dana", "Then you chose it."),
    Line("gil", "So what do I do?"),
    Line("dana", "Try again in January. Fresh deductible."),
)


SCRIPT = scripting.Script(LINES)
say, part, hold = SCRIPT.say, SCRIPT.part, SCRIPT.hold


BEATS = (
    say(0.0, "frog", 0, "wide", "o", "desk", "toast:0"),  # the hook: the claim already on his phone
    say(2.4, "dog", 1, "closed", "grin", "lean"),
    say(4.2, "frog", 2, "half", "flat", "desk"),
    say(5.4, "dog", 3, "half", "smirk", "desk", "tick:212"),
    hold(7.2, "frog", "", "down", "flat", "sigh", "toast:1"),  # the denial buzzes in
    say(8.0, "frog", 4, "narrow", "open", "crossed"),
    Beat(10.0, "dog", "The hospital is.", "half", "grin", "lean", 5, 0, "tick:388"),
    part(11.2, "dog", 5, 3, "The doctor isn't.", "closed", "smirk", "lean"),
    say(12.6, "frog", 6, "shock", "o", "face"),
    say(14.0, "dog", 7, "half", "flat", "desk", "tick:640"),
    say(15.0, "frog", 8, "wide", "o", "desk"),
    say(15.8, "dog", 9, "closed", "smirk", "lean"),
    hold(17.0, "frog", "", "down", "drop", "face2", "toast:2"),  # the ambulance bill
    say(18.2, "frog", 10, "shock", "open", "face2"),
    hold(19.6, "dog", LINES[10].text, "side", "flat", "type"),  # the hold: she types while he waits
    hold(20.9, "dog", LINES[10].text, "half", "none", "desk", "tick:999"),
    Beat(21.6, "dog", "Try again in January.", "half", "smirk", "lean", 11, 0),  # the punchline
    part(23.0, "dog", 11, 4, "Fresh deductible.", "closed", "grin", "lean"),
    hold(24.6, "frog", "", "down", "flat", "desk", "hangup"),  # the sting; he looks at his other arm
    hold(26.0, "frog", "", "narrow", "smirk", "crossed", "page:JAN 1"),  # January
    hold(27.4, "frog", "", "narrow", "grin", "crossed", "toast:3"),  # the button: a new claim
)
SKETCH = Sketch(SLUG, TITLE, (GIL, DANA), LINES, BEATS, END)


def pages(beats) -> list[tuple[float, str]]:
    """The calendar through the sketch: the first page from 0, then every ``page:`` event."""
    return scripting.changes(beats, "page", FIRST_PAGE)


def ticks(beats) -> list[tuple[float, int]]:
    """The board's counts: :data:`FIRST_WAITING` from 0, then every ``tick:`` event; they only climb."""
    out = [(0.0, FIRST_WAITING)]
    for at, arg in sketch.events(beats, "tick"):
        if not arg.isdigit() or int(arg) <= out[-1][1] or int(arg) > toon_sets.WAITING_MAX:
            raise sketch.SketchError(f"the board climbs to at most {toon_sets.WAITING_MAX}: tick {arg!r} at {at} s")
        out.append((at, int(arg)))
    return out


def waiting_through(beats, start: float, end: float) -> list[tuple[float, int]]:
    """What the board shows from ``start`` to ``end`` (project seconds): the count at ``start`` from 0, then each
    tick inside."""
    counts = ticks(beats)
    first = [n for t, n in counts if t <= start][-1]
    return [(0.0, first)] + [(t, n) for t, n in counts if start < t < end]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and fall in
    Gil's shots (the phone is his), and so do the calendar's pages, which parse and rise; ticks climb and fall in
    Dana's shots (the board is hers); exactly one hangup; no other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if who_at[at] != "frog":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: the phone is in Gil's shot")
    try:
        toon_sets.parse_pages(pages(sk.beats))
    except ToonDataError as err:
        raise sketch.SketchError(f"the calendar: {err}") from err
    for at, _ in sketch.events(sk.beats, "page"):
        if who_at[at] != "frog":
            raise sketch.SketchError(f"the page at {at} s turns off screen: the calendar is in Gil's shot")
    for at, _ in sketch.events(sk.beats, "tick"):
        if who_at[at] != "dog":
            raise sketch.SketchError(f"the tick at {at} s is off screen: the board is in Dana's shot")
    ticks(sk.beats)
    scripting.exactly_once(sk.beats, "hangup", "the call ends exactly once")
    scripting.only_events(sk.beats, {"toast", "page", "tick", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Gil's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Gil's shots: the home office at night with the tear-off calendar, his phone's claims in front. Dana's: the
    call-centre cubicle, its board counting the calls waiting through the shot. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "frog":
        toon_sets.home(cv, shot.back, end=shot.end)
        toon_sets.calendar(cv, shot.back, pages(shot.beats))
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts)
    else:
        toon_sets.call_centre(cv, shot.back, waiting_through(shot.beats, app.start, app.end), end=shot.end)
    shot.badges(BADGES)
