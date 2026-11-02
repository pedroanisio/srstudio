"""Small Print #2, the paper: Rafa, main trigger challenge, the episode as data.

The question people type is whether paper folds in half more than seven times. He is already folding when the reel
opens, and stalls at seven. Each fold doubles the layers, so seven folds is 128, and each fold needs about four times
the paper (Gallivan's formula, 2001). In 2002 Britney Gallivan folded one sheet twelve times, with tissue paper four
thousand feet long (Guinness World Records). The button: so yes, you can, and he will need a longer kitchen, a roll
running off his worktop and out of the frame. Then he starts again at fold four, the first frame.
"""

from __future__ import annotations

from srstudio import foley as synth
from srstudio import smallprint
from srstudio.rafa_reel import cut
from srstudio.smallprint import Beat, Show, Stamp
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SLUG = "paper-fold"
PAPER, ROLL = "smallprint-paper", "smallprint-roll"
SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
FOLDING = ((0.8, "fold-5"), (1.6, "fold-6"))  # seconds into the question: he folds while he asks
BEATS = (
    Beat("hook", "Can you fold paper in half eight times?", BATTERY, PAPER, "fold-4", steps=FOLDING),
    Beat("try", "Seven. And... nope.", MELTDOWN, framing="tight", steps=((0.25, "fold-7"),), hold=0.6),
    Beat(
        "layers",
        "Every fold doubles the layers. Seven folds is 128.",
        BATTERY,
        panel="fold-layers",
        stamp=Stamp("7 FOLDS = 128 LAYERS", "Arithmetic: 2 x 2 x 2 x 2 x 2 x 2 x 2 = 128"),
    ),
    Beat(
        "four",
        "Each fold needs about four times the paper.",
        BATTERY,
        panel="fold-layers",
        stamp=Stamp("4x THE PAPER, EVERY FOLD", "Britney Gallivan's folding formula, 2001"),
    ),
    Beat(
        "record",
        "In 2002, a high school student did twelve. One sheet of tissue, 4,000 feet long.",
        SMILE,
        panel="long-strip",
        stamp=Stamp("12 FOLDS, 2002", "Guinness World Records, record of 27 Jan 2002"),
    ),
    Beat("yes", "So yes, you can. I'll need a longer kitchen.", BATTERY, ROLL, "roll", hold=0.6),
    Beat("end", "Right. Eight.", BATTERY, PAPER, "fold-4"),
)
# Seconds, measured from the takes.
KEPT = (2.057, 1.659, 3.995, 2.462, 5.474, 2.136, 0.892)
SHOW = Show(
    slug=SLUG,
    number=2,
    title="Can you fold paper in half more than 7 times? — Small Print #2",
    question="Can you fold a paper in half more than 7 times?",
    description="Rafa folds a sheet of paper until it stops him, then reads the small print on the record.",
    accessibility=(
        "A clay man in a teal cardigan over mustard stands at a kitchen worktop folding a sheet of paper that gets "
        "smaller and thicker. A search box over him asks whether you can fold a paper in half more than seven times. "
        "At seven it is a lump and he gives up. A page of ruled paper shows a stack of layers doubling while a count "
        "climbs from 1 to 128, stamped in red: 7 folds = 128 layers, then 4x the paper, every fold. A strip of "
        "paper runs across the page without end under the words 4,000 ft of tissue paper, stamped: 12 folds, 2002. "
        "Back at the worktop a roll of tissue runs off the counter and out of the frame, and he starts again."
    ),
    beats=BEATS,
    kept=KEPT,
    post=InstagramPost(
        title="Can you fold a paper in half more than 7 times?",
        description=(
            "Small Print #2. Every fold doubles the layers and needs about four times the paper. In 2002 Britney "
            "Gallivan folded one sheet 12 times, using tissue paper 4,000 ft long (Guinness World Records)."
        ),
        credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
        hashtags=("#math", "#paperfolding", "#explained", "#animation", "#smallprint"),
        thumbnail=Thumbnail(
            "More than\n7 folds?",
            1.0,
            "Small Print #2",
            focus=(540.0, 760.0),
            zoom=1.0,
            place="bottom",
            accent="#FF9F7A",
        ),  # fmt: skip
    ),
)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The shared sounds, a crease for every fold he makes, and the roll running off the worktop."""
    sound = smallprint.sounder(root, end, seed)
    hook, attempt = SHOW.beat("hook", beats).start, SHOW.beat("try", beats).start
    folds = [cut(hook + at) for at, _ in FOLDING] + [cut(attempt + 0.25)]
    yes, last = SHOW.beat("yes", beats).start, SHOW.beat("end", beats).start
    return [
        *smallprint.shared_sounds(SHOW, beats, end, root, seed),
        sound("crease", -9.0, synth.PAPER_CRUNCH, folds),
        sound("unroll", -14.0, synth.SWISH, [cut(yes)]),
        sound("again", -12.0, synth.PAPER_CRUNCH, [cut(last) + 0.1]),
    ]
