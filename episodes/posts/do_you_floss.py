"""The release of do-you-floss."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "do-you-floss",
    InstagramPost(
        title="Every day.",
        description=(
            "She has an answer ready. He has a photograph.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); every character "
            "is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Charlie and Matilda. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#dentist",
            "#flossing",
            "#liedtomydentist",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Do you floss?", 0.6, "Toon 27"),
    ),
    tags=Tags(
        "money-services",
        "protagonist",
        "embarrassment",
        recurring=("fern", "rex"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-clipboard": 1,
        "toon-dog": 2,
        "toon-frog": 2,
    },
)
