"""The Unwritten Rules #2, a present: Rafa, main trigger recognition, the sketch as data.

You have to love a present, show it being used and keep it findable, for life, because the giver may visit. He says so
with a smile, holding the mug the whole reel has been about, and then breaks rule one: he gave it back. To her, for her
birthday, in the same paper. She said she loved it. The smile comes back on a cut, because his birthday is Tuesday.
"""

from __future__ import annotations

from srstudio import foley as synth
from srstudio import rafa_show
from srstudio.rafa_show import Beat, Show
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SLUG = "unwritten-rules-present"
ID_MUG, ID_PHONE, ID_FOLDER = "rafa-mug", "rafa-phone", "rafa-bills"
SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
BEATS = (
    Beat("hook", "Nobody tells you a present has rules.", SMILE, ID_MUG, label="A PRESENT HAS RULES"),
    Beat("one", "Rule one. You love it. Whatever it is.", SMILE, ID_MUG, label="RULE 1", hold=0.3),
    Beat("two", "Rule two. You send a photo. You, using it.", SMILE, ID_PHONE, label="RULE 2"),
    Beat("three", "Rule three. The one nobody admits.", BATTERY, ID_FOLDER, label="RULE 3"),
    Beat("where", "You know where it is. In case they visit.", BATTERY, ID_FOLDER, "close", hold=1.4),
    Beat("break", "I gave it back.", BATTERY, ID_MUG, "tight", hold=0.5, gain=-5.0),
    Beat("her", "To her. For her birthday.", MELTDOWN, ID_MUG),
    Beat("same", "Same mug. Same paper.", MELTDOWN, ID_MUG, insert=ID_MUG),
    Beat("loved", "She said she loved it.", MELTDOWN, ID_MUG, "tight", hold=1.3, gain=-3.0),
    Beat("tuesday", "My birthday's Tuesday.", SMILE, ID_MUG, hold=0.7),
    Beat("off", rafa_show.SIGN_OFF, SMILE, ID_MUG),
)
KEPT = (1.948, 1.999, 2.665, 2.668, 2.094, 1.017, 1.572, 1.483, 1.219, 1.359, 1.32)  # seconds, measured from the takes
SHOW = Show(
    slug=SLUG,
    number=2,
    title="A present has rules — The Unwritten Rules #2",
    description="Rafa, 34, mostly functional, explains the unwritten rules of a present, and breaks the first one.",
    accessibility=(
        "A clay man in a teal cardigan over mustard stands at a kitchen worktop and talks to camera with a tired "
        "smile, a mug that says I'm great, I think, under his hand. He gives three rules of a present. The mug becomes "
        "a phone, then a folder marked adult life, pending. He admits he gave the mug back to the woman who gave it to "
        "him, and his eyes go wide. The mug fills the frame. On a cut the smile is back, and he says his birthday is "
        "Tuesday, then you know what you did."
    ),
    beats=BEATS,
    kept=KEPT,
    post=InstagramPost(
        title="What do you do with a present you hate?",
        description="The Unwritten Rules #2. Rafa, 34, mostly functional, has rules.",
    credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
        hashtags=("#presents", "#unwrittenrules", "#animation", "#adulting"),
        thumbnail=Thumbnail("A present\nhas rules", 4.0, "The Unwritten Rules #2", focus=(540.0, 700.0), zoom=1.0,
                            place="bottom"),  # fmt: skip
    ),
    stop="break",
)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The shared sounds, a clock through the longest silence, the paper on "Same paper." and a bell on the smile."""
    sound, said = rafa_show.sounder(root, end, seed), SHOW.said(speech)
    clock = said["where"][1] + 0.25
    return [
        *rafa_show.shared_sounds(SHOW, beats, end, speech, root, seed),
        sound("clock", -16.0, synth.REMOTE_CLICK, [clock, clock + 0.7]),
        sound("paper", -10.0, synth.SWISH, [SHOW.beat("same", beats).start + 0.5]),
        sound("ting", -9.0, synth.BELL, [SHOW.beat("tuesday", beats).start]),
    ]
