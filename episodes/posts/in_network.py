"""The release of in-network."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "in-network",
    InstagramPost(
        title="Is a broken arm covered?",
        description=(
            "Gil calls his insurer about a broken arm. Dana in claims is delighted: which arm? They cover the right. "
            "The doctor's out of network, the ambulance was his choice, and the advice is to try again in January.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Chris (Gil) and Jessica (Dana), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Jessica. Original characters, drawn in code.",
        hashtags=(
            "#healthinsurance",
            "#adulting",
            "#customerservice",
            "#onhold",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Is a broken arm\ncovered?", 0.8, "Toon 09", (500, 1181), 1.3),
    ),
)
