"""The release of upside-down."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

from ._interview import SERIES

RELEASE = Release(
    "upside-down",
    InstagramPost(
        title="When the Q3 numbers are bad, check the board.",
        description=(
            "Episode 07 of The Interview. The candidate got a job after all: reception. Upstairs the boss presents "
            "a chart going down, until the speakerphone points out the board is upside down. Record quarter! "
            "Bonuses for everyone! Including reception? Flip.\n"
            "Episode 09, in the new polished reception and conference room."
        ),
        credit="Voices: ElevenLabs premade voices Eric, Will and Liam. Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#quarterlyreview", "#bonus"),
        thumbnail=Thumbnail("Check\nthe board.", 19.2, "The Interview · 09", (700, 760), 1.25),
    ),
)
