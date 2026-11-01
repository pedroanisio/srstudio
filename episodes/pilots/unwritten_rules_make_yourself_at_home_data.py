"""The Unwritten Rules #4, make yourself at home: Rafa, main trigger recognition, the sketch as data.

"Make yourself at home" is an instruction not to: you refuse water twice, and when they wipe the table you have four
minutes. He breaks rule one: she said it, so he did, in March. This is her kitchen, the one the show has been in all
along. Keys come out in the silence, a door opens, and on a cut the smile comes back. "Just leaving."

The one reel of the seven on a still opening (L7): he stands very politely still in someone else's kitchen.
"""

from __future__ import annotations

from srstudio import foley as synth
from srstudio import rafa_show
from srstudio.rafa_show import Beat, Show
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SLUG = "unwritten-rules-make-yourself-at-home"
ID_MUG, ID_PHONE, ID_FOLDER, ID_TOTE = "rafa-mug", "rafa-phone", "rafa-bills", "rafa-tote"
SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
BEATS = (
    Beat(
        "hook", "Nobody tells you a visit has rules.", SMILE, ID_MUG, label="MAKE YOURSELF AT HOME HAS RULES"
    ),  # fmt: skip
    Beat("one", "Rule one. Do not make yourself at home.", SMILE, ID_MUG, label="RULE 1", hold=0.4),
    Beat("two", "Rule two. Say no twice. The third time, water.", SMILE, ID_PHONE, label="RULE 2", hold=0.3),
    Beat("three", "Rule three. The one nobody admits.", BATTERY, ID_FOLDER, label="RULE 3"),
    Beat("wipe", "They wipe the table, you have four minutes.", BATTERY, ID_FOLDER, "close", hold=1.4),
    Beat("break", "She said make yourself at home.", BATTERY, ID_MUG, "tight", hold=0.5, gain=-3.0),
    Beat("did", "So I did.", MELTDOWN, ID_TOTE),
    Beat("march", "That was in March.", MELTDOWN, ID_TOTE, "close"),
    Beat("kitchen", "This is her kitchen.", MELTDOWN, ID_TOTE, "tight", hold=1.3, gain=-5.0),
    Beat("leaving", "Just leaving.", SMILE, ID_TOTE, hold=0.7),
    Beat("off", rafa_show.SIGN_OFF, SMILE, ID_MUG),
)
KEPT = (1.935, 2.188, 4.037, 2.668, 2.321, 1.632, 0.676, 1.046, 0.916, 0.766, 1.325)  # seconds, measured from the takes
SHOW = Show(
    slug=SLUG,
    number=4,
    title="Make yourself at home has rules — The Unwritten Rules #4",
    description=(
        "Rafa, 34, mostly functional, explains the unwritten rules of make yourself at home, and breaks the first one."
    ),
    accessibility=(
        "A clay man in a teal cardigan over mustard stands at a kitchen worktop and talks to camera with a tired "
        "smile, a mug that says I'm great, I think, under his hand. He gives three rules of being a guest. The mug "
        "becomes a phone, then a folder marked adult life, pending. He admits he was told to make himself at home in "
        "March and did, and that this is her kitchen. Keys jingle and a door opens. On a cut the smile is back, a tote "
        "bag under his hand, and he says just leaving, then you know what you did."
    ),
    beats=BEATS,
    kept=KEPT,
    post=InstagramPost(
        title="Does make yourself at home ever mean it?",
        description="The Unwritten Rules #4. Rafa, 34, mostly functional, has rules.",
        credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
        hashtags=("#guests", "#unwrittenrules", "#animation", "#adulting"),
        thumbnail=Thumbnail(
            "A visit\nhas rules", 4.0, "The Unwritten Rules #4", focus=(540.0, 700.0), zoom=1.0, place="bottom"
        ),  # fmt: skip
    ),
    stop="break",
    push=(2.4, 1.0),
)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """The shared sounds, a clock in the wiped-table hold, and in the last silence keys, then the door opening."""
    sound, said = rafa_show.sounder(root, end, seed), SHOW.said(speech)
    clock = said["wipe"][1] + 0.25
    keys = said["kitchen"][1] + 0.1
    return [
        *rafa_show.shared_sounds(SHOW, beats, end, speech, root, seed),
        sound("clock", -16.0, synth.REMOTE_CLICK, [clock, clock + 0.7]),
        sound("keys", -12.0, synth.KEYS, synth.jingle(keys, seed)),
        sound("door", -12.0, synth.SCRAPE, [keys + 0.85]),
        sound("ting", -10.0, synth.BELL, [SHOW.beat("leaving", beats).start]),
    ]
