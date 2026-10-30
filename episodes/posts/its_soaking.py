"""The release of its-soaking."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "its-soaking",
    InstagramPost(
        title="Day 1. It's soaking.",
        description=(
            "It has been soaking for some time now. Nobody is allowed to touch it.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Will (the roommate) and Roger (the landlord); every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Roger. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#roommates",
            "#dirtydishes",
            "#sharedhouse",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("It's soaking.", 0.5, "Toon 26"),
    ),
    tags=Tags(
        "relationships", "other-person", "recognition", test="sp-hook_motion", arm="a", recipient="b", to="roommate"
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-clipboard": 1,
        "toon-kitchen": 1,
        "toon-rabbit": 2,
        "toon-raccoon": 2,
        "toon-sloth": 1,
    },
)
