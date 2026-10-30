"""The release of regards-dad."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "regards-dad",
    InstagramPost(
        title="Dear Son. Understood. Regards, Dad.",
        description=(
            "Gary writes every text as a formal letter. He has not yet worked out what a thumbs-up means, and he is "
            "sitting in the next chair.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary) and Sarah (Priya), with Priya "
            "lip-synced to her words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris and Sarah. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#dads", "#family", "#texting", "#parents", "#relatable", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Dear\nSon.", 5.0, "Collage 18", None, 1.0, place="bottom"),
    ),
    tags=Tags(
        "family",
        "other-person",
        "affection",
        recurring=("gary", "kai", "priya"),
        test="sp-hook_motion",
        arm="a",
        recipient="b",
        to="family",
    ),
    style="Collage",
    parts={"collage-gary": 1, "collage-kai": 1, "collage-priya": 1, "signature-cactus": 1, "signature-code": 1},
    parts={
        "collage-arm": 1,
        "collage-bubble": 1,
        "collage-dining-room": 1,
        "collage-gary": 1,
        "collage-kai": 1,
        "collage-phone": 1,
        "collage-priya": 1,
        "collage-salt-shaker": 1,
        "collage-tablecloth": 1,
        "collage-thumb": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
