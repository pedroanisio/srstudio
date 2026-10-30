"""The release of password-expired."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "password-expired",
    InstagramPost(
        title="Why does my password expire every month?",
        description=(
            "Bruno's password expired again. IT rejects the new one: too similar to the old one. How does IT know "
            "his old one? They keep them all, in a spreadsheet. Was the spreadsheet password protected? It was. It "
            "expired.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Bill (Bruno) and Alice (Pip), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Bill and Alice. Original characters, drawn in code.",
        hashtags=(
            "#passwords",
            "#ithelpdesk",
            "#cybersecurity",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Why does my\npassword expire?", 1.0, "Toon 13", (470, 1130), 1.35),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-bear": 1,
        "toon-board-text": 1,
        "toon-captions": 1,
        "toon-clock": 1,
        "toon-desk": 1,
        "toon-meeting": 1,
        "toon-mug": 1,
        "toon-notes": 1,
        "toon-rabbit": 1,
        "toon-room": 1,
        "toon-toast": 1,
    },
)
