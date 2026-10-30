"""The release of cleaning-fee."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "cleaning-fee",
    InstagramPost(
        title="We paid the cleaning fee. Why am I repainting the fence?",
        description=(
            "Fern paid the holiday rental's cleaning fee. The checkout list says strip the beds, run the dishwasher, "
            "take out the trash and repaint the fence, just the front. The cleaner checks her work. Then the late "
            "checkout fee arrives.\n"
            "A Toon sketch with Fern and Rex, voiced with ElevenLabs premade voices Matilda and Charlie; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda (Fern) and Charlie (Rex). Buzz and sting synthesised.",
        hashtags=(
            "#cleaningfee",
            "#vacationrental",
            "#checkout",
            "#travelhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Cleaning fee: $150.\nNow repaint the fence.", 1.0, "Toon 19"),
    ),
    tags=Tags(
        "money-services", "other-person", "recognition", recurring=("fern", "rex"), test="sp-hook_motion", arm="b"
    ),
)
