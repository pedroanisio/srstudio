"""Your Rent — the sketch as data: every parent is outraged by what you pay in rent, right up to the moment they
work out what they could charge.

Fern and Lewis sit across Dad's kitchen table and Fern says the number. Dad, who has hated every boyfriend, is
appalled for her, puts a hoof on her hand and offers her old room back: eighteen hundred, utilities included. Lewis
leans in and asks if that is for both of them. Dad looks at him for the first time. He is twenty-two hundred.

Three voices (ElevenLabs premade Brian as Dad, Matilda as Fern, Will as Lewis), one kitchen
(:func:`srstudio.toon_sets.kitchen`) and the table's edge (:func:`srstudio.toon_house.ledge`) with Dad's mug on it
(:func:`srstudio.toon_props.mug`). Two framings hold more than one of them: the three-shot and the two-shot where his
hoof lands on her hand, each from :func:`srstudio.toon_pair.figure`, acted by ``ROWS``; the close-ups are the
default lead shots. The viewer's own line is up from the first frame until the first line ends (:func:`opening`,
:mod:`srstudio.opener`). :func:`validate` checks the events; :func:`dress` draws each shot, :func:`lens` its camera
and :func:`sounds` the room.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, foley, opener, scripting, sketch, toon_house, toon_pair, toon_props, toon_sets
from srstudio.scripting import at
from srstudio.sketch import Beat, Line, Sketch
from srstudio.toon import fx, fy
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.toon_voices import speaker, tinted
from srstudio.voice import Transcript, TranscriptMismatch, check_transcript

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3212
SLUG = "your-rent"
TITLE = "Your Rent — Dad, Fern and Lewis (Toon)"
DESCRIPTION = (
    "A Toon sketch at Dad's kitchen table: he is outraged by what his daughter pays in rent, right up to the moment "
    "he works out what he could charge."
)
ACCESSIBILITY = (
    "An old cartoon goat sits at his kitchen table with a steaming mug. Across from him a young frog and a young "
    "raccoon sit side by side. She tells him her rent and he freezes. He leans over, puts a hoof on her hand and "
    "offers her old room back, then names a price, utilities included. The raccoon leans in hopefully and asks if "
    "that is for both of them. The goat looks at him for the first time and names a bigger price. A line of text "
    "over the opening reads: my dad finding out my rent. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Brian (Dad), Matilda (Fern) and Will (Lewis)."
NOTE = "ElevenLabs premade voices Brian, Matilda and Will at their natural pace; no reference-voice cloning."
DAD = speaker("dad", "Brian", "goat", "deadpan")
FERN = speaker("fern", "Matilda", "frog")
LEWIS = speaker("lewis", "Will", "raccoon", "deadpan")
TINTS = tinted(DAD, FERN, LEWIS)
TEXT = "my dad finding out my rent"  # the viewer's own line (send-v2)
NAMES = ("fern", "lewis", "brian", "matilda", "will")
OPENER_TOP = 460.0  # frame px: under the caption band (334 to 429), over every face
THREE, TWO = "hamster", "sloth"  # never seen: the names of the three-shot and the two-shot
BARE = (THREE, TWO)

THREE_SCALE = 0.62
DAD_THREE, FERN_THREE, LEWIS_THREE = (130.0, 822.0), (326.0, 822.0), (455.0, 822.0)  # paws on the table top
TWO_SCALE = 0.72
DAD_TWO, FERN_TWO = (104.0, 812.0), (380.0, 812.0)  # each "lean" paw reaches 184 px at full size: they meet
MUG_X = 362.0  # reference px of the mug's left side in a close on Dad, clear of his paws and the cactus
MUG_THREE = (150.0, 0.62)  # where it stands in the three-shot and how big, in front of him

LINES = (
    Line("fern", "It's twenty-two hundred."),
    Line("dad", "A year?"),
    Line("fern", "A month."),
    Line("dad", "For one room? That's robbery."),
    Line("dad", "Move home. Your room's still there."),
    Line("fern", "Really, Dad?"),
    Line("dad", "Eighteen hundred. Utilities included."),
    Line("lewis", "For both of us?"),
    Line("dad", "You're twenty-two hundred."),
)
script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
TOP = ("up", "flat", "desk")  # what a bare shot's beat holds: nobody is its lead
PRICES = {0: "It's $2,200.", 6: "$1,800. Utilities included."}  # the lines said as words, captioned in dollars


def priced(start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = "") -> Beat:
    """The beat that starts line ``line``, its amount captioned in figures with the currency (arc4d3's dollar rule,
    Slack 1793499862.755999); :func:`validate` holds the figures to the words said."""
    return Beat(start, who, PRICES[line], eyes, mouth, arms, line, 0, event)


# Dad: appalled for her, then a landlord
SIPS = Act("left", "flat", "desk")
FROZEN = Act("shock", "none", "desk")
HOOF = Act("side", "flat", "lean")
# Fern: matter-of-fact, then touched
SAYS = Act("left", "flat", "desk")
HAND = Act("side", "flat", "lean")  # mirrored: she looks at him, her paw out on the table
TOUCHED = Act("teary", "grin", "lean")
# Lewis: beside her, hopeful
BESIDE = Act("left", "flat", "desk")
REST = Act("half", "flat", "desk")

ROWS = (
    (hold(0.0, THREE, "", *TOP), SIPS, SAYS, BESIDE),
    (priced(0.3, THREE, 0, *TOP), SIPS, SAYS, BESIDE),
    (say(1.7, "goat", 1, "shock", "flat", "desk"), FROZEN, SAYS, BESIDE),
    (say(2.3, "frog", 2, "half", "flat", "desk"), FROZEN, SAYS, BESIDE),
    (first(3.1, "goat", 3, "For one room?", "wide", "open", "desk"), FROZEN, SAYS, BESIDE),
    (part(4.1, "goat", 3, 3, "That's robbery.", "narrow", "flat", "desk"), FROZEN, SAYS, BESIDE),
    (say(5.2, TWO, 4, *TOP, "hoof"), HOOF, HAND, REST),
    (say(7.2, "frog", 5, "teary", "grin", "desk"), HOOF, TOUCHED, REST),
    (priced(8.2, "goat", 6, "half", "flat", "desk"), HOOF, TOUCHED, REST),
    (say(10.2, "raccoon", 7, "wide", "grin", "lean"), HOOF, TOUCHED, REST),
    (hold(11.4, "goat", "", "side", "none", "desk", "look"), HOOF, TOUCHED, REST),  # [1.2 s]: he sees Lewis
    (say(12.6, "goat", 8, "narrow", "flat", "desk"), HOOF, TOUCHED, REST),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"goat": tuple(r[1] for r in ROWS), "frog": tuple(r[2] for r in ROWS), "raccoon": tuple(r[3] for r in ROWS)}
ONCE = ("hoof", "look")
HELD = 1.2  # seconds of the hold before the last line: no speech, no new caption
END = 13.95  # the cut comes on "hundred": the last take ends at 13.87
SKETCH = Sketch(SLUG, TITLE, (DAD, FERN, LEWIS), LINES, BEATS, END, tail=0.1, bare=BARE)
HUM = replace(foley.HUM, seconds=1.6)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, every caption in dollars reads as the words said, the hoof lands
    once and Dad's look comes once, after it, and holds with no line and no caption until the last line."""
    sketch.check(sk)
    for b in sk.beats:
        if b.line in PRICES:
            if (b.caption, b.word) != (PRICES[b.line], 0):
                raise sketch.SketchError(f"line {b.line} is captioned {b.caption!r}, not its price {PRICES[b.line]!r}")
            try:
                check_transcript(Transcript("en", 1.0, b.caption.replace("$", ""), ()), sk.lines[b.line].text)
            except TranscriptMismatch as exc:
                raise sketch.SketchError(f"line {b.line}'s figures are not the words said: {exc}") from None
    scripting.speaks_by(sk.beats, 0.5)
    scripting.only_events(sk.beats, set(ONCE))
    for kind in ONCE:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    if at(sk.beats, "look") <= at(sk.beats, "hoof"):
        raise sketch.SketchError("Dad looks at Lewis after the hoof lands")
    look = next(i for i, b in enumerate(sk.beats) if b.event == "look")
    after = sk.beats[look + 1]
    if not (after.line == len(sk.lines) - 1 and after.start - sk.beats[look].start >= HELD - 0.05):
        raise sketch.SketchError(f"the look holds {HELD} s and the last line follows it")


def opening(cv, parent, said, measure):
    """The viewer's own line, from the first frame until the first line stops."""
    return opener.draw(cv, parent, TEXT, said, measure=measure, top=OPENER_TOP, names=NAMES)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The fridge across the room through the held look."""
    return (Sound("hum", HUM, (round(at(beats, "look") - 0.2, 3),), -22.0),)


def _mug(shot, x: float, scale: float, steam: bool) -> None:
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), anchorX=fx(x), anchorY=fy(838.0), x=fx(x), y=fy(838.0), scaleX=scale,
                 scaleY=scale)  # fmt: skip
    toon_props.mug(cv, g, x, ((0.0, shot.end),) if steam else ())


def _three(shot) -> None:
    """Dad on his side of the table, facing them; Fern and Lewis side by side on theirs."""
    cv = shot.cv
    toon_sets.kitchen(cv, shot.back, chair=False)
    toon_pair.figure(shot, shot.back, "goat", DAD_THREE, ACTS["goat"], scale=THREE_SCALE, mirror=True)
    toon_pair.figure(shot, shot.back, "frog", FERN_THREE, ACTS["frog"], scale=THREE_SCALE)
    toon_pair.figure(shot, shot.back, "raccoon", LEWIS_THREE, ACTS["raccoon"], scale=THREE_SCALE)
    toon_house.ledge(cv, shot.front, "oak")
    _mug(shot, *MUG_THREE, steam=True)


def _two(shot) -> None:
    """Dad and Fern at the corner of the table, his hoof on her hand."""
    cv = shot.cv
    toon_sets.kitchen(cv, shot.back, chair=False)
    toon_pair.figure(shot, shot.back, "frog", FERN_TWO, ACTS["frog"], scale=TWO_SCALE, mirror=True)
    toon_pair.figure(shot, shot.back, "goat", DAD_TWO, ACTS["goat"], scale=TWO_SCALE)  # his hoof over her hand
    toon_house.ledge(cv, shot.front, "oak")


def dress(shot) -> None:
    """The kitchen in its two group framings, and behind every close-up; Dad's mug in front of him in his."""
    who = shot.app.who
    if who == THREE:
        _three(shot)
        return
    if who == TWO:
        _two(shot)
        return
    toon_sets.kitchen(shot.cv, shot.back, chair=False)
    toon_house.ledge(shot.cv, shot.front, "oak")
    if who == "goat":
        _mug(shot, MUG_X, 1.0, steam=shot.app.start < at(shot.beats, "hoof"))


def lens(shot, setup) -> None:
    """A slow push from the first frame on the three of them, its pivot low and right so both marks stay whole."""
    if shot.app.start == 0.0:
        camera.anchor(setup, 880.0, 1200.0, place=True)
        camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (shot.app.end, 1.06)])
