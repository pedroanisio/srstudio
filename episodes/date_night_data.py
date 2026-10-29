"""Date Night — the sketch as data: Otto sends Mae a calendar invite for dinner, from the next room. There is an
agenda: item three, feelings, ten minutes, with time left for questions. She is optional; the pasta is required.
She accepts. It is recurring. Until June. That is when their lease ends. He is very organised. Then he shares a
spreadsheet: apartments.

Two voices (ElevenLabs premade Sarah as Mae, Daniel as Otto), one shot per speaker, the same flat: Mae in the
kitchen with the date on the fridge, Otto in the home office next door with a tear-off calendar that jumps to the
end date when he names it. Otto's invite, agenda and spreadsheet arrive as toasts on Mae's phone (``toast:``
events). Both characters are lip-synced to their own takes. ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`dress` draws each shot's set and props
(``_toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon_props, toon_sets
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.toon import ToonDataError
from srstudio.voice import Voice, VoiceSettings

SEED = 1081
SLUG = "date-night"
TITLE = "Date Night — Mae and Otto (Toon)"
DESCRIPTION = (
    "A Toon sketch at home: Otto sends Mae a calendar invite for dinner, from the next room. There is an agenda. "
    "She is optional. It is recurring, until June, when their lease ends. He is very organised."
)
ACCESSIBILITY = (
    "A cartoon rabbit in a kitchen talks on a video call with a cartoon bear in the home office next door. Phone "
    "notifications slide in over her window: a dinner invite, an agenda, her status as optional and, at the end, "
    "a shared spreadsheet of apartments. The tear-off calendar behind him jumps from October to June 30. Their "
    "lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae) and Daniel (Otto); synthesised keyboard, buzz and sting."
NOTE = "ElevenLabs premade voices Sarah and Daniel at their natural pace; no reference-voice cloning."
MAE = Speaker(
    "mae",
    Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "rabbit",
)
OTTO = Speaker(
    "otto",
    Voice(role="otto", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.25),
    "bear",
)
TINTS = {"mae": "#fbd3e0", "otto": "#d8e4f4"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"rabbit": "Otto, next room", "bear": "Mae, in the kitchen"}
FRIDGE = "DATE NIGHT 8PM"
FIRST_PAGE = "OCT 29"
TOASTS = (
    ("Otto", "Invite: Date night"),
    ("Otto", "3. Feelings (10 min)"),
    ("Otto", "Mae: optional"),
    ("Otto", "Shared: apartments.xlsx"),
)
END = 31.0

LINES = (
    Line("mae", "A calendar invite? For dinner?"),
    Line("otto", "Date night. There's an agenda."),
    Line("mae", "Item three. Feelings. Ten minutes."),
    Line("otto", "I left time for questions."),
    Line("mae", "You marked me optional."),
    Line("otto", "You're optional. The pasta is required."),
    Line("mae", "Fine. Accepted."),
    Line("otto", "Great. It's recurring."),
    Line("mae", "Until when?"),
    Line("otto", "June."),
    Line("mae", "That's when our lease ends."),
    Line("otto", "I'm very organized."),
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
    say(0.0, "rabbit", 0, "narrow", "flat", "crossed", "toast:0"),  # the hook: the invite already on her phone
    say(2.6, "bear", 1, "half", "smirk", "desk"),
    hold(4.8, "rabbit", "", "down", "flat", "crossed", "toast:1"),  # the agenda buzzes in
    say(5.6, "rabbit", 2, "narrow", "flat", "crossed"),
    say(8.0, "bear", 3, "closed", "grin", "lean"),
    hold(10.0, "rabbit", "", "down", "flat", "sigh", "toast:2"),  # her status
    say(10.8, "rabbit", 4, "narrow", "flat", "crossed"),
    Beat(12.6, "bear", "You're optional.", "half", "flat", "desk", 5, 0),
    part(13.8, "bear", 5, 2, "The pasta is required.", "closed", "smirk", "lean"),
    say(15.6, "rabbit", 6, "half", "flat", "sigh"),
    say(17.0, "bear", 7, "wide", "grin", "lean"),
    say(18.6, "rabbit", 8, "narrow", "o", "crossed"),
    hold(19.6, "bear", LINES[8].text, "side", "flat", "desk"),  # the hold: he checks the calendar
    hold(20.9, "bear", LINES[8].text, "half", "none", "desk"),
    say(21.6, "bear", 9, "half", "flat", "desk", "page:JUN 30"),  # the punchline: the calendar jumps to it
    say(22.8, "rabbit", 10, "shock", "drop", "face2"),
    hold(24.6, "bear", LINES[10].text, "closed", "none", "crossed"),  # the hold before the button line
    say(25.9, "bear", 11, "half", "smirk", "lean"),
    hold(27.4, "rabbit", "", "closed", "none", "face", "hangup"),  # the sting
    hold(28.6, "rabbit", "", "narrow", "flat", "crossed", "toast:3"),  # the button: he shares the apartments
)
SKETCH = Sketch(SLUG, TITLE, (MAE, OTTO), LINES, BEATS, END)


def pages(beats) -> list[tuple[float, str]]:
    """The calendar through the sketch: the first page from 0, then every ``page:`` event."""
    return [(0.0, FIRST_PAGE)] + sketch.events(beats, "page")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and fall in
    Mae's shots (the phone is hers); calendar pages parse, rise and turn in Otto's shot (the calendar is his);
    the note fits the fridge; exactly one hangup; no other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if who_at[at] != "rabbit":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: the phone is in Mae's shot")
    try:
        toon_sets.parse_pages(pages(sk.beats))
    except ToonDataError as err:
        raise sketch.SketchError(f"the calendar: {err}") from err
    for at, _ in sketch.events(sk.beats, "page"):
        if who_at[at] != "bear":
            raise sketch.SketchError(f"the page at {at} s turns off screen: the calendar is in Otto's shot")
    if len(FRIDGE) > toon_sets.NOTE_MAX:
        raise sketch.SketchError(f"the fridge note {FRIDGE!r} does not fit ({toon_sets.NOTE_MAX})")
    if len(sketch.events(sk.beats, "hangup")) != 1:
        raise sketch.SketchError("the call ends exactly once")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"toast", "page", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Mae's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Mae's shots: the kitchen with the date on the fridge and the coffee machine, her phone's toasts in front.
    Otto's: the home office at night, his desk lamp lit, a plant, and the tear-off calendar on the wall that
    jumps to the end date. Both carry the call badge."""
    cv, app = shot.cv, shot.app
    if app.who == "rabbit":
        toon_sets.kitchen(cv, shot.back, note=FRIDGE)
        toon_sets.coffee_machine(cv, shot.back)
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts)
    else:
        toon_sets.home(cv, shot.back, end=shot.end)
        toon_sets.calendar(cv, shot.back, pages(shot.beats))
        toon_sets.desk_lamp(cv, shot.back, lit=[(app.start, app.end)])
        toon_sets.plant(cv, shot.back)
    shot.badges(BADGES)
