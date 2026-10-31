"""The release of its-gone."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "its-gone",
    InstagramPost(
        title="Gone where?",
        description=(
            "What did you touch?\n"
            "A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa) and Chris (Gary), lip-synced to "
            "their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda and Chris. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#techsupport", "#parents", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("It's gone.", 1.0, "Collage"),
    ),
    tags=Tags("family", "other-person", "affection", recurring=("rosa", "gary"), test="sp-hook_motion", arm="b"),
    style="Collage",
    comedy=Scores(author=18, reviewer=17),
    parts={
        "collage-arm": 1,
        "collage-boardroom": 1,
        "collage-gary": 1,
        "collage-living-room": 1,
        "collage-phone": 1,
        "collage-rosa": 1,
        "collage-router": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
