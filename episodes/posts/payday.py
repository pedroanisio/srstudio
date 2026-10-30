"""The release of payday."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "payday",
    InstagramPost(
        title="Eleven seconds. That is how long payday lasted.",
        description=(
            "The salary lands and Deb punches the air. Then the bills march in, including a gym that closed in 2023 "
            "and a charge nobody can explain, and the bank tells her she has earned a treat.\n"
            "A Collage sketch voiced with the ElevenLabs premade voice Jessica (Deb), lip-synced to her words; every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voice: ElevenLabs premade voice Jessica. Original characters, drawn in code. Sound effects synthesised "
            "in code."
        ),
        hashtags=("#payday", "#bills", "#adulting", "#money", "#relatable", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Payday!", 0.8, "Collage 18", None, 1.0, place="bottom"),
    ),
    tags=Tags(
        "money-services",
        "institution",
        "recognition",
        recurring=("deb",),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Collage",
    parts={"collage-deb": 1, "collage-sign": 1, "signature-cactus": 1, "signature-code": 1},
    parts={
        "collage-bill": 1,
        "collage-bubble": 1,
        "collage-bus-stop": 1,
        "collage-confetti": 1,
        "collage-deb": 1,
        "collage-phone": 1,
        "collage-sign": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
