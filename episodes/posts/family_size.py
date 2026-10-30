"""The release of family-size."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "family-size",
    InstagramPost(
        title="The bag got bigger. The chip did not.",
        description=(
            "Rosa opens a family size bag of chips and it breathes out for three seconds. Inside is one chip, and "
            "the clerk explains which family it was meant for.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa) and Brian (Brent), lip-synced to "
            "their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda and Brian. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#groceries", "#shrinkflation", "#supermarket", "#chips", "#relatable", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Family\nsize.", 1.0, "Collage 18", None, 1.0, place="bottom"),
    ),
    tags=Tags(
        "money-services",
        "institution",
        "recognition",
        recurring=("rosa", "brent"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Collage",
    parts={"collage-brent": 1, "collage-rosa": 1, "collage-sign": 1, "signature-cactus": 1, "signature-code": 1},
)
