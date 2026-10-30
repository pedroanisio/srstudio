"""The release of fee-for-asking."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "fee-for-asking",
    InstagramPost(
        title="One concert ticket, forty dollars. Then the fees started.",
        description=(
            "Deb buys one ticket at the box office. Brent adds a convenience fee, convenient for him, a facility "
            "fee, a fee to print it at home and the service, which is him reading the fees. Then she asks about the "
            "last line.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb) and Brian (Brent), lip-synced to "
            "their words; the venue is invented, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica and Brian. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#hiddenfees",
            "#concerttickets",
            "#servicefee",
            "#prices",
            "#relatable",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("One ticket for\nSaturday, please.", 0.5, "Collage 16", (600, 1000), 1.3, place="bottom"),
    ),
    tags=Tags(
        "money-services", "institution", "recognition", recurring=("deb", "brent"), test="sp-hook_motion", arm="a"
    ),
    characters={"collage-brent": 1, "collage-deb": 1},
)
