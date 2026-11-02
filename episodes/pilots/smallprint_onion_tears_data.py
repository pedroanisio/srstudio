"""Small Print #3, the onion: Rafa, main trigger utility, the episode as data.

The question people type is why onions make you cry. He is mid-chop and already crying, and says he's fine. Cutting
breaks the onion's cells, and an enzyme turns what they let out into a gas (Imai et al., Nature, 2002), which reaches
the eyes; tears wash it out (University of Wisconsin-Madison, 2009). The gas is syn-propanethial-S-oxide (Silvaroli
et al., 2017); its name stays off the screen, because it does not read as a stamp. What the sources back: chill it
first, since cold slows the enzymes (University of Wisconsin-Madison, 2009), and use a sharp knife, which throws fewer
and slower droplets (Wu et al., PNAS, 2025). The button: the onion is done and he is still crying, and that one's
not the onion.
"""

from __future__ import annotations

from srstudio import foley as synth
from srstudio import smallprint
from srstudio.rafa_reel import cut
from srstudio.smallprint import Beat, Show, Stamp
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SLUG = "onion-tears"
ONION = "smallprint-onion"
SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
CHOP = 0.45  # seconds between two strokes of the knife
STROKES = ("half-down", "half-up", "chopped-down", "chopped-up", "chopped-down", "chopped-up", "chopped-down")
CHOPPING = tuple((round(CHOP * (i + 1), 3), state) for i, state in enumerate(STROKES))
BEATS = (
    Beat("hook", "Why do onions make you cry? I'm fine. It's the onion.", MELTDOWN, ONION, "half-up", steps=CHOPPING,
         tears=True, hold=0.5),
    Beat(
        "gas",
        "Cutting breaks its cells. That lets out a gas.",
        BATTERY,
        panel="onion-gas",
        stamp=Stamp("IT'S A GAS", "Imai et al., Nature, 2002; University of Wisconsin-Madison, 2009"),
    ),
    Beat("eyes", "It reaches your eyes, and tears wash it out.", BATTERY, panel="onion-gas"),
    Beat(
        "cold",
        "Chill it first. Cold slows the whole thing down.",
        SMILE,
        panel="onion-fix",
        stamp=Stamp("CHILL IT FIRST", "University of Wisconsin-Madison, 2009"),
    ),
    Beat(
        "sharp",
        "And use a sharp knife. It sprays fewer droplets.",
        SMILE,
        panel="onion-fix",
        stamp=Stamp("SHARP KNIFE, FEWER DROPLETS", "Wu et al., PNAS, 2025"),
        hold=0.4,
    ),
    Beat("done", "Cold onion. Sharp knife. Done.", BATTERY, ONION, "chopped-down", framing="close", tears=True,
         hold=0.9),
    Beat("end", "That one's not the onion.", MELTDOWN, ONION, "half-up", tears=True),
)  # fmt: skip
# Seconds, measured from the takes.
KEPT = (3.537, 2.846, 2.546, 3.005, 2.759, 1.705, 1.277)
SHOW = Show(
    slug=SLUG,
    number=3,
    title="Why do onions make you cry? — Small Print #3",
    question="Why do onions make you cry?",
    description="Rafa chops an onion in tears and reads the small print on why, and on what helps.",
    accessibility=(
        "A clay man in a teal cardigan over mustard chops an onion on a board at a kitchen worktop, wide-eyed, with "
        "tears on his cheeks. A search box over him asks why onions make you cry. He says he's fine, it's the onion. "
        "A page of ruled paper shows an onion's cut rings, its cells popping one by one and green wisps rising to a "
        "drawn eye that drips a tear, stamped in red: it's a gas. A second page shows a cold onion with a falling "
        "thermometer and a sharp knife throwing a few droplets, stamped: chill it first, then sharp knife, fewer "
        "droplets. Back at the worktop the onion is chopped and he is still crying: that one's not the onion."
    ),
    beats=BEATS,
    kept=KEPT,
    post=InstagramPost(
        title="Why do onions make you cry?",
        description=(
            "Small Print #3. Cutting breaks the onion's cells and makes a gas that reaches your eyes (Imai et al., "
            "Nature, 2002). Chilling it first slows that down (UW-Madison, 2009), and a sharp knife throws fewer "
            "droplets (Wu et al., PNAS, 2025)."
        ),
        credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
        hashtags=("#cooking", "#science", "#explained", "#animation", "#smallprint"),
        thumbnail=Thumbnail(
            "Why onions\nmake you cry",
            1.0,
            "Small Print #3",
            focus=(540.0, 760.0),
            zoom=1.0,
            place="bottom",
            accent="#FF9F7A",
        ),  # fmt: skip
    ),
)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The shared sounds, the knife on the board at every stroke down, and a sniff-sized breath on the button."""
    sound = smallprint.sounder(root, end, seed)
    hook = SHOW.beat("hook", beats).start
    downs = [cut(hook + at) for at, state in CHOPPING if state.endswith("down")]
    done = SHOW.beat("done", beats).start
    return [
        *smallprint.shared_sounds(SHOW, beats, end, root, seed),
        sound("chop", -8.0, synth.KNOCK, downs),
        sound("last-chop", -8.0, synth.KNOCK, [cut(done)]),
    ]
