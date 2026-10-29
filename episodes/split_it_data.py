"""Split It — the sketch as data: Brock and Mia at the end of dinner. Should they just split it evenly? Mia had a side
salad. Brock had the lobster; same thing, basically. He had three. Small ones, and the wine was for the table. Mia
does not drink; he knows, so he had hers. Fine: evenly. Great. Oh no, his card is declined. Of course it is. Mia pays
the lot and Brock will send his half tonight. Her phone buzzes: Brock sent her $6.50, for half her salad. Then: same
place Friday?

Two voices (ElevenLabs premade Roger as Brock, River as Mia), one shot per speaker across the same bistro table
(:mod:`srstudio.toon_dinner`): Brock behind a plate of empty lobster shells, the wine bottle and his glass, the check
in its folder in front of him; Mia behind her side salad, a glass of water and her empty wine glass, the card reader
by her plate. The reader's screen changes on ``reader:`` events, the payments arrive on Mia's phone as toasts
(``toast:`` events), the sting plays on ``hangup``. ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`dress` lays each shot's table.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import sketch, toon_dinner, toon_props
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1102
SLUG = "split-it"
TITLE = "Split It — Brock and Mia (Toon)"
DESCRIPTION = (
    "A Toon sketch at dinner: Brock wants to split the bill evenly. Mia had a side salad; he had three lobsters and "
    "her wine. His card is declined, she pays, and he sends her his half: of her salad."
)
ACCESSIBILITY = (
    "A cartoon bear and a cartoon rabbit sit across a restaurant table with a white tablecloth, in a booth under a "
    "chalk SPECIALS board that reads LOBSTER, MARKET PRICE. The bear has a plate of empty lobster shells, a wine "
    "bottle and a full glass; the rabbit has a side salad, a glass of water and an empty wine glass. A card reader "
    "reads DECLINED, then APPROVED. Notifications slide in over the rabbit: her payment, the bear's transfer of "
    "$6.50 for half her salad, and an invitation to the same place on Friday. Their lines appear in tinted pills "
    "and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Roger (Brock) and River (Mia); synthesised buzz and sting."
NOTE = "ElevenLabs premade voices Roger and River at their natural pace; no reference-voice cloning."
BROCK = Speaker(
    "brock",
    Voice(role="brock", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "bear",
)
MIA = Speaker(
    "mia",
    Voice(role="mia", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.30),
    "rabbit",
)
TINTS = {"brock": "#f3dcc0", "mia": "#f6d6e4"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
TOASTS = (
    ("Bank", "Paid: $428.60"),
    ("Brock", "Sent you $6.50"),
    ("Brock", "For: half your salad"),
    ("Brock", "Same place Friday?"),
)
TOAST_SIZE = 36  # the punchline is on the phone: larger than the toasts of earlier sketches
READER = (0.0, "TAP CARD", "idle")
SCREENS = {"DECLINED": "bad", "APPROVED": "good"}
# What stands on each side of the table, reference x on the cloth; the check is in front of Brock from the start.
LAID = {
    "bear": (("check", 196), ("shells", 290), ("wine", 400), ("glass", 456)),
    "rabbit": (("salad", 200), ("water", 290), ("empty", 352)),
}
READER_X = {"bear": 84, "rabbit": 452}
END = 31.0

LINES = (
    Line("brock", "Should we just split it evenly?"),
    Line("mia", "I had a side salad."),
    Line("brock", "I had the lobster. Same thing, basically."),
    Line("mia", "You had three lobsters."),
    Line("brock", "Small ones. And the wine was for the table."),
    Line("mia", "I don't drink."),
    Line("brock", "I know. So I had yours."),
    Line("mia", "Fine. Evenly."),
    Line("brock", "Great. Oh no. My card's declined."),
    Line("mia", "Of course it is."),
    Line("brock", "I'll send you my half. Tonight."),
)


def say(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, LINES[line].text, eyes, mouth, arms, line, 0, event)


def part(start: float, who: str, line: int, word: int, caption: str, eyes: str, mouth: str, arms: str,
         event: str = "") -> Beat:  # fmt: skip
    """A beat on a later word of a line, captioned with that part of it (a long line in two pills)."""
    if caption not in LINES[line].text or LINES[line].text.split()[word] != caption.split()[0]:
        raise sketch.SketchError(f"{caption!r} is not line {line} from word {word}")
    return Beat(start, who, caption, eyes, mouth, arms, line, word, event)


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    return Beat(start, who, caption, eyes, mouth, arms, None, None, event)


BEATS = (
    say(0.0, "bear", 0, "wide", "grin", "lean"),  # the hook, the check already on the table
    say(2.4, "rabbit", 1, "half", "flat", "desk"),
    Beat(4.0, "bear", "I had the lobster.", "closed", "grin", "lean", 2, 0, ""),
    part(5.4, "bear", 2, 4, "Same thing, basically.", "half", "smirk", "lean"),
    say(7.0, "rabbit", 3, "narrow", "flat", "crossed"),
    Beat(8.6, "bear", "Small ones.", "side", "smirk", "desk", 4, 0, ""),
    part(9.6, "bear", 4, 2, "And the wine was for the table.", "half", "grin", "lean"),
    say(11.6, "rabbit", 5, "narrow", "flat", "crossed"),
    say(12.8, "bear", 6, "closed", "grin", "lean"),
    hold(14.6, "rabbit", "", "down", "flat", "sigh"),  # the sigh
    say(15.8, "rabbit", 7, "half", "flat", "crossed"),
    Beat(17.0, "bear", "Great.", "closed", "grin", "lean", 8, 0, ""),
    part(18.0, "bear", 8, 1, "Oh no. My card's declined.", "shock", "o", "face", "reader:DECLINED"),
    say(20.0, "rabbit", 9, "narrow", "flat", "type", "reader:APPROVED"),  # she taps her own card
    hold(21.2, "rabbit", "", "down", "flat", "desk", "toast:0"),
    say(22.4, "bear", 10, "closed", "grin", "lean"),
    hold(24.4, "rabbit", "", "half", "flat", "crossed"),  # the hold: she waits for his half
    hold(25.8, "rabbit", "", "down", "o", "desk", "toast:1"),
    hold(27.0, "rabbit", "", "shock", "drop", "face", "toast:2"),  # the punchline: half her salad
    hold(28.3, "rabbit", "", "narrow", "flat", "face2", "hangup"),  # the sting
    hold(29.4, "rabbit", "", "narrow", "flat", "crossed", "toast:3"),  # the button: same place Friday?
)
SKETCH = Sketch(SLUG, TITLE, (BROCK, MIA), LINES, BEATS, END)


def screens(beats) -> list[tuple[float, str, str]]:
    """The card reader through the sketch: :data:`READER` from 0, then every ``reader:`` event."""
    out = [READER]
    for at, arg in sketch.events(beats, "reader"):
        if arg not in SCREENS:
            raise sketch.SketchError(f"the reader shows one of {sorted(SCREENS)}, got {arg!r} at {at} s")
        out.append((at, arg, SCREENS[arg]))
    return out


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: toasts index ``TOASTS`` and fall in
    Mia's shots (the phone is hers); the reader declines in Brock's shot and approves in Mia's, once each, in that
    order; exactly one hangup (the sting), after the last spoken line; no other events."""
    sketch.check(sk)
    who_at = {b.start: b.who for b in sk.beats}
    for at, arg in sketch.events(sk.beats, "toast"):
        if not (arg.isdigit() and int(arg) < len(TOASTS)):
            raise sketch.SketchError(f"toast {arg!r} at {at} s is not one of {len(TOASTS)} toasts")
        if who_at[at] != "rabbit":
            raise sketch.SketchError(f"the toast at {at} s buzzes off screen: the phone is in Mia's shot")
    shown = screens(sk.beats)
    if [s[1] for s in shown[1:]] != ["DECLINED", "APPROVED"]:
        raise sketch.SketchError("the reader declines Brock's card, then approves Mia's, once each")
    if who_at[shown[1][0]] != "bear" or who_at[shown[2][0]] != "rabbit":
        raise sketch.SketchError("the reader declines in Brock's shot and approves in Mia's")
    hangups = sketch.events(sk.beats, "hangup")
    if len(hangups) != 1:
        raise sketch.SketchError("the sting plays exactly once")
    if hangups[0][0] < max(b.start for b in sk.beats if b.spoken):
        raise sketch.SketchError("the sting comes after the last line")
    unknown = {b.event.split(":")[0] for b in sk.beats if b.event} - {"toast", "reader", "hangup"}
    if unknown:
        raise sketch.SketchError(f"unknown events {sorted(unknown)}")


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that arrive during one of Mia's shots, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Both sides of one table in the bistro booth: each shot lays its speaker's dishes and the card reader, whose
    screen follows the whole sketch; Mia's shots carry her phone's toasts."""
    cv, app = shot.cv, shot.app
    toon_dinner.restaurant(cv, shot.back)
    toon_dinner.dishes(cv, shot.front, LAID[app.who], id=cv.uid("dish"))
    toon_dinner.card_reader(
        cv, shot.front, screens(shot.beats), at=(READER_X[app.who], toon_dinner.TABLE_Y), id=cv.uid("card-reader")
    )
    if app.who == "rabbit":
        toasts = toasts_in(shot.beats, app)
        if toasts:
            toon_props.toasts(cv, shot.front, toasts, size=TOAST_SIZE)
