"""The release of date-night."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "date-night",
    InstagramPost(
        title="A calendar invite? For dinner?",
        description=(
            "Otto sends Mae a calendar invite for date night, from the next room. There's an agenda: item three, "
            "feelings, ten minutes. She's optional; the pasta is required. It's recurring. Until June.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Sarah (Mae) and Daniel (Otto), lip-synced to "
            "their words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Sarah and Daniel. Original characters, drawn in code.",
        hashtags=(
            "#datenight",
            "#relationshiphumor",
            "#couplegoals",
            "#calendarinvite",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("A calendar invite.\nFor dinner.", 0.8, "Toon 08", (470, 1130), 1.35),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-bear": 1,
        "toon-calendar": 1,
        "toon-captions": 1,
        "toon-coffee-machine": 1,
        "toon-desk": 1,
        "toon-desk-lamp": 1,
        "toon-home": 1,
        "toon-kitchen": 1,
        "toon-plant": 1,
        "toon-rabbit": 1,
        "toon-toast": 1,
    },
)
