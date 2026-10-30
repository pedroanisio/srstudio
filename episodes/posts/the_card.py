"""The release of the-card."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-card",
    InstagramPost(
        title="Rex, whose card is this?",
        description=(
            "There's a leaving card in the office kitchen. Fern signs it without asking whose it is: good luck out "
            "there. Then she reads the front. It says Fern. She is not leaving. There's a meeting with HR. Rex has "
            "advice: bring it with you.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#leavingcard",
            "#layoffs",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Whose card\nis this?", 0.8, "Toon 14", (470, 1130), 1.35),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-board-text": 1,
        "toon-captions": 1,
        "toon-desk": 1,
        "toon-dog": 1,
        "toon-frog": 1,
        "toon-kitchen": 1,
        "toon-meeting": 1,
        "toon-note-insert": 1,
    },
)
