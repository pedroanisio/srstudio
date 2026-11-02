"""Small Print #1, the penny: Rafa, main trigger myth reversal, the episode as data.

The question people type is whether a penny dropped from the Empire State Building can kill someone. He lets one go
off the clay tower on his worktop. It cannot: a penny is flat, so it tumbles, and tumbling it tops out at about
twenty-five miles an hour (Bloomfield, 2012); MythBusters busted it in 2003. The button turns the question round: what
does hit that building is lightning, about twenty-three times a year (NASA Goddard citing NOAA, 2017), so up there
the penny is the safe one. Nobody is ever drawn under the drop, and he asks you not to check.
"""

from __future__ import annotations

from srstudio import foley as synth
from srstudio import smallprint
from srstudio.rafa_reel import cut
from srstudio.smallprint import Beat, Show, Stamp
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SLUG = "penny-drop"
TOWER = "smallprint-tower"
SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
FALL = ((0.7, "fall-1"), (0.95, "fall-2"), (1.2, "fall-3"), (1.45, "landed"))  # seconds into "Okay. One penny."
BEATS = (
    Beat("hook", "Can a penny from up there kill you?", SMILE, TOWER, "top"),
    Beat("try", "Okay. One penny.", MELTDOWN, framing="tight", steps=FALL, hold=0.7),
    Beat("no", "Nope. It would sting.", BATTERY, framing="close"),
    Beat(
        "why",
        "A penny is flat, so it tumbles. It tops out around 25 miles an hour.",
        BATTERY,
        panel="penny-fall",
        stamp=Stamp("TOPS OUT AT 25 MPH", "Louis Bloomfield, Univ. of Virginia, in Live Science, 2012"),
    ),
    Beat(
        "busted",
        "MythBusters tried it in 2003. Busted.",
        BATTERY,
        panel="penny-fall",
        stamp=Stamp("BUSTED", "MythBusters, Discovery Channel, 2003"),
    ),
    Beat("check", "Please don't check.", BATTERY, TOWER, "landed", framing="tight", hold=0.5),
    Beat(
        "bolt",
        "What does hit that building? Lightning. About twenty-three times a year.",
        SMILE,
        panel="lightning",
        stamp=Stamp("HIT 23 TIMES A YEAR", "NASA Goddard, citing NOAA, 2017"),
    ),
    Beat("end", "So up there, the penny's the safe one.", SMILE, TOWER, "top"),
)
# Seconds, measured from the takes.
KEPT = (1.845, 1.017, 1.624, 4.475, 2.58, 0.958, 4.59, 1.903)
SHOW = Show(
    slug=SLUG,
    number=1,
    title="Can a penny dropped from the Empire State Building kill you? — Small Print #1",
    question="Can a penny dropped from the Empire State Building kill you?",
    description="Rafa lets a penny go off a clay skyscraper and reads the small print on falling coins.",
    accessibility=(
        "A clay man in a teal cardigan over mustard stands at a kitchen worktop by a clay model skyscraper with a "
        "penny on its top. A search box over him asks whether a penny dropped from the Empire State Building can "
        "kill you. He lets it go, wide-eyed, and it tumbles to the worktop. A page of ruled paper shows a penny "
        "tumbling past a tower and a speed bar that stops at 25 miles an hour, stamped in red: tops out at 25 mph. "
        "A second stamp says busted. He asks you not to check. A drawn bolt strikes the tower's spire while tally "
        "marks count to 23, stamped: hit 23 times a year. Back at the worktop the penny is on top again."
    ),
    beats=BEATS,
    kept=KEPT,
    post=InstagramPost(
        title="Can a penny dropped from the Empire State Building kill you?",
        description=(
            "Small Print #1. Short answer: it would sting. A penny tumbles, and tumbling it tops out around 25 mph "
            "(Louis Bloomfield, 2012). What does hit the building is lightning, about 23 times a year (NASA, citing "
            "NOAA, 2017). Please don't test it."
        ),
        credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
        hashtags=("#physics", "#mythbusting", "#explained", "#animation", "#smallprint"),
        thumbnail=Thumbnail(
            "Can a penny\nkill you?",
            1.0,
            "Small Print #1",
            focus=(540.0, 760.0),
            zoom=1.0,
            place="bottom",
            accent="#FF9F7A",
        ),  # fmt: skip
    ),
)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The shared sounds, the penny's ring on the worktop where it lands, and a thunder roll under each bolt."""
    sound = smallprint.sounder(root, end, seed)
    landed = cut(SHOW.beat("try", beats).start + FALL[-1][0])
    bolt = SHOW.beat("bolt", beats).start
    first = cut(bolt)
    return [
        *smallprint.shared_sounds(SHOW, beats, end, root, seed),
        sound("tink", -8.0, synth.COIN, [landed]),
        sound("whoosh", -16.0, synth.SWISH, [cut(SHOW.beat("try", beats).start + FALL[0][0]) - 0.1]),
        sound("thunder", -14.0, synth.RUMBLE, [first + 0.5, first + 2.0]),
    ]
