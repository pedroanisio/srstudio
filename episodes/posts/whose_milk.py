"""The release of whose-milk."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "whose-milk",
    InstagramPost(
        title="Rex. Whose milk is this?",
        description=(
            "The milk in the office fridge says Rex, 2019. It has survived two reorgs, more than Dave did. Then it "
            "moved. It's not milk anymore: it's yogurt, and it got promoted. Fern has been here six years.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#officefridge",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Whose milk\nis this?", 0.8, "Toon 06", (470, 1130), 1.35),
    ),
    characters={"toon-dog": 1, "toon-frog": 1},
)
