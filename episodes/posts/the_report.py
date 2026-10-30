"""The release of the-report."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-report",
    InstagramPost(
        title="Rex. It's on your forehead.",
        description=(
            "Fern wants the report. Rex has never heard of any report. The eleven reminders, the sticky notes and "
            "the one on his forehead say otherwise.\n"
            "A Toon two-hander voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Charlie and Matilda. Original characters, drawn in code.",
        hashtags=(
            "#officehumor",
            "#workcomedy",
            "#thereport",
            "#animatedshorts",
            "#vectoranimation",
            "#cartoondog",
            "#cartoonfrog",
        ),
        thumbnail=Thumbnail("It's on your\nforehead.", 27.5, "Toon 03", (330, 1000), 1.4),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-board-text": 1,
        "toon-captions": 1,
        "toon-clock": 1,
        "toon-desk": 1,
        "toon-dog": 1,
        "toon-frog": 1,
        "toon-meeting": 1,
        "toon-mug": 1,
        "toon-notes": 1,
        "toon-room": 1,
        "toon-toast": 1,
    },
)
