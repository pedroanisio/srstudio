"""The release of like-family."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "like-family",
    InstagramPost(
        title="Rex, can we talk about my salary?",
        description=(
            "We're not a company, Rex says, we're a family. Then Fern would like an allowance. He thinks of her "
            "like a daughter. Then she'll see him at Christmas. Let's keep this professional. So, a raise? Sorry. "
            "She's like family.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
        hashtags=("#salary", "#payraise", "#werefamily", "#officehumor", "#workcomedy", "#animatedshorts", "#lipsync"),
        thumbnail=Thumbnail("Can we talk about\nmy salary?", 0.8, "Toon 16", (470, 1130), 1.35),
    ),
    characters={"toon-dog": 1, "toon-frog": 1},
)
