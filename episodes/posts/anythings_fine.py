"""The release of anythings-fine."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "anythings-fine",
    InstagramPost(
        title="Anything's fine. Except that. And that. And that.",
        description=(
            "Priya asks what Gary wants for dinner. Anything's fine, he says, and then he refuses the entire "
            "city, one takeout menu at a time, until the delivery app starts to worry about them.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary) and Sarah (Priya), lip-synced to "
            "their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris and Sarah. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#dinner", "#couples", "#relationships", "#marriedlife", "#relatable", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Anything's\nfine.", 2.0, "Collage 18", None, 1.0, place="bottom"),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "recognition",
        recurring=("gary", "priya"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="partner",
    ),
    style="Collage",
    parts={
        "collage-alarm-clock": 1,
        "collage-bedroom": 1,
        "collage-cereal-box": 1,
        "collage-duvet": 1,
        "collage-food": 1,
        "collage-gary": 1,
        "collage-living-room": 1,
        "collage-phone": 1,
        "collage-priya": 1,
        "collage-sign": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
