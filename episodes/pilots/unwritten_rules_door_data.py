"""The Unwritten Rules #3, a door: Rafa, main trigger recognition, the sketch as data.

A door has a distance: too far and you didn't see them, close and you hold it, and in between they have to do a small
pretend jog, for you. He breaks rule one: he held it for a man in the parking lot, who jogged, who is ninety. That was
at lunch. He is still holding it, which the picture cannot show, because no door is drawn in his world. So the sound
carries it: steps come in faint on "He jogged." and get nearer to the last frame, and on a cut the smile comes back and
he calls out to someone off camera.
"""

from __future__ import annotations

from srstudio import foley as synth
from srstudio import rafa_show
from srstudio.rafa_show import Beat, Show
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SLUG = "unwritten-rules-door"
ID_MUG, ID_PHONE, ID_FOLDER = "rafa-mug", "rafa-phone", "rafa-bills"
SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
STEP = 0.62  # seconds between a ninety-year-old's jogging steps
STEP_FROM, STEP_TO = -34.0, -9.0  # the gain of the first step and the last
STEP_TIERS = 6  # a track for each level of nearness
BEATS = (
    Beat("hook", "Nobody tells you a door has rules.", SMILE, ID_MUG, label="HOLDING A DOOR HAS RULES"),
    Beat("one", "Rule one. Too far, you didn't see them.", SMILE, ID_MUG, label="RULE 1", hold=0.3),
    Beat("two", "Rule two. Too near, you hold it. You're not an animal.", SMILE, ID_PHONE, label="RULE 2"),
    Beat("three", "Rule three. The one nobody admits.", BATTERY, ID_FOLDER, label="RULE 3"),
    Beat("jog", "In between, they have to jog. A tiny, pretend jog.", BATTERY, ID_FOLDER, "close", hold=1.4),
    Beat("break", "I held it.", BATTERY, ID_MUG, "tight", hold=0.5, gain=-5.0),
    Beat("far", "He was in the parking lot.", MELTDOWN, ID_MUG),
    Beat("jogged", "He jogged.", MELTDOWN, ID_MUG, "close"),
    Beat("ninety", "He's ninety.", MELTDOWN, ID_MUG, "close"),
    Beat("lunch", "That was at lunch.", MELTDOWN, ID_MUG, "tight", hold=1.3, gain=-3.0),
    Beat("nearly", "Nearly there!", SMILE, ID_MUG, hold=0.7),
    Beat("off", rafa_show.SIGN_OFF, SMILE, ID_MUG),
)
# Seconds, measured from the takes.
KEPT = (1.934, 2.305, 3.577, 2.705, 3.178, 0.645, 1.152, 0.734, 0.845, 0.948, 0.781, 1.32)
SHOW = Show(
    slug=SLUG,
    bleed=True,
    number=3,
    title="Holding a door has rules — The Unwritten Rules #3",
    description=(
        "Rafa, 34, mostly functional, explains the unwritten rules of holding a door, and breaks the first one."
    ),
    accessibility=(
        "A clay man in a teal cardigan over mustard stands at a kitchen worktop and talks to camera with a tired "
        "smile, a mug that says I'm great, I think, under his hand. He gives three rules of holding a door. The mug "
        "becomes a phone, then a folder marked adult life, pending. He admits he held one for a man in the parking "
        "lot, who is ninety, and his eyes go wide. Slow footsteps can be heard, faint at first, coming nearer. On a "
        "cut the smile is back, and he calls out nearly there, then you know what you did."
    ),
    beats=BEATS,
    kept=KEPT,
    post=InstagramPost(
        title="How far away is too far to hold a door?",
        description="The Unwritten Rules #3. Rafa, 34, mostly functional, has rules.",
        credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
        hashtags=("#manners", "#unwrittenrules", "#animation", "#adulting"),
        thumbnail=Thumbnail(
            "A door\nhas rules", 4.0, "The Unwritten Rules #3", focus=(540.0, 700.0), zoom=1.0, place="bottom"
        ),  # fmt: skip
    ),
    stop="break",
)


def steps(beats, end: float) -> list[list[float]]:
    """The man's steps from "He jogged." to the last frame, one list for each level of nearness, the nearest last."""
    first = SHOW.beat("jogged", beats).start
    count = int((end - 0.05 - first) / STEP) + 1
    times = [round(first + i * STEP, 3) for i in range(count)]
    return [times[i * count // STEP_TIERS : (i + 1) * count // STEP_TIERS] for i in range(STEP_TIERS)]


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The shared sounds, the door's creak when he holds it, and the steps: faint, then nearer, right to the end."""
    sound = rafa_show.sounder(root, end, seed)
    tiers = [
        sound(f"steps-{i}", STEP_FROM + (STEP_TO - STEP_FROM) * i / (STEP_TIERS - 1), synth.KNOCK, times)
        for i, times in enumerate(steps(beats, end))
        if times
    ]
    return [
        *rafa_show.shared_sounds(SHOW, beats, end, speech, root, seed),
        sound("door", -14.0, synth.SCRAPE, [SHOW.beat("break", beats).start + 0.1]),
        *tiers,
    ]
