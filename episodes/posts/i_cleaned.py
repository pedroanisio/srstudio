"""The release of i-cleaned."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "i-cleaned",
    InstagramPost(
        title="He cleaned. Do not open anything.",
        description=(
            "Everything is exactly where he put it, which is out of sight.\n"
            "A Toon sketch, voiced with ElevenLabs premade voices Will and Jessica; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will (the raccoon) and Jessica (the hedgehog). Foley synthesised.",
        hashtags=("#roommates", "#roommatelife", "#cleaning", "#animatedshorts", "#comedyshorts", "#cartoon"),
        thumbnail=Thumbnail("I cleaned!", 1.5, "Toon 30"),
    ),
    tags=Tags(
        "relationships", "other-person", "recognition", test="sp-hook_motion", arm="b", recipient="b", to="roommate"
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-closet": 1,
        "toon-flat": 1,
        "toon-front-door": 1,
        "toon-goat": 1,
        "toon-hedgehog": 2,
        "toon-laundry-pile": 1,
        "toon-oven": 1,
        "toon-paw": 1,
        "toon-plates": 1,
        "toon-raccoon": 2,
        "toon-shower": 1,
        "toon-sparkles": 1,
        "toon-tiny-drawer": 1,
        "toon-whirl": 1,
        "toon-worktop": 1,
    },
)
