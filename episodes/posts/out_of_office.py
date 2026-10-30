"""The release of out-of-office."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "out-of-office",
    InstagramPost(
        title="Aren't you on vacation?",
        description=(
            "Bruno is on vacation. Out-of-office is on. He has answered every email to say so, personally, because "
            "it's warmer. The calendar tears through the week. Even his boss replied: from her vacation.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#outofoffice",
            "#vacation",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Aren't you on\nvacation?", 0.8, "Toon 07", (470, 1222), 1.4),
    ),
    characters={"toon-bear": 1, "toon-rabbit": 1},
)
