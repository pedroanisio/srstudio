"""The release of premium-suction."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "premium-suction",
    InstagramPost(
        title="Why did you stop cleaning?",
        description=(
            "The robot vacuum's free trial has ended. You bought the hardware; suction is monthly. The kitchen is "
            "premium, the corners platinum. What's free? It maps your home and sells the map. Guess who bought it.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Lily."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Lily. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#subscriptions",
            "#smarthome",
            "#landlords",
            "#techhumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Your free trial\nhas ended.", 2.6, "Ink 06", place="top"),
    ),
    cover=True,
)
