"""The release of nail-hole."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "nail-hole",
    InstagramPost(
        title="Original features",
        description=(
            "Ever lost a deposit to a nail hole?\n"
            "A Collage sketch voiced with ElevenLabs premade voices Alice (Feld) and Jessica (Deb), lip-synced to "
            "their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice and Jessica. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#landlord", "#renting", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("A nail hole.", 6.5, "Collage"),
    ),
    tags=Tags(
        "money-services", "other-person", "recognition", recurring=("feld", "deb"), test="sp-hook_motion", arm="b"
    ),
    style="Collage",
    comedy=Scores(author=17, reviewer=17),
    parts={
        "collage-bill": 1,
        "collage-deb": 1,
        "collage-feld": 1,
        "collage-living-room": 1,
        "collage-phone": 1,
        "collage-sign": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        # collage-magnifying-glass is drawn too; it stays out until it is approved: a release cannot pin a proposed
        # version.
    },
)
