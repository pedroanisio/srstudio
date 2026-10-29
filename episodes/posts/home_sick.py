"""The release of home-sick."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "home-sick",
    InstagramPost(
        title="Why won't you open the door?",
        description=(
            "Your video doorbell won't let you in: the resident is home sick today. You got better? Then you're late "
            "for work. So it asks the street's group chat who you are, from your account. Your boss lives on the "
            "street.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and George."
        ),
        credit="Voices: ElevenLabs premade voices Chris and George. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#sickday",
            "#smarthome",
            "#neighbors",
            "#officehumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("The resident\nis home sick.", 4.0, "Ink 07", place="top"),
    ),
    cover=True,
)
