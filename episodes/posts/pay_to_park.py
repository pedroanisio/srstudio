"""The release of pay-to-park.

Take 06, "Biscuit.": Biskit: operator-approved STT spelling, 2026-10-29, after two takes (1.06, 1.0).
"""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "pay-to-park",
    InstagramPost(
        title="Coins? How retro.",
        description=(
            "The parking meter won't take your coin. Download the app, create an account, choose a password with a "
            "capital, a symbol and a childhood memory. Enable location. Rate your parking experience. Session "
            "started.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Laura."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Laura. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#parking",
            "#parkingapp",
            "#techhumor",
            "#everydaylife",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Coins?\nHow retro.", 2.3, "Ink 08", place="bottom"),
    ),
    cover=True,
    tags=Tags("everyday-tech", "institution", "recognition", recurring=("doodle",)),
)
