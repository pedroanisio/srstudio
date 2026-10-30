"""The release of fee-for-asking."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "fee-for-asking",
    InstagramPost(
        title="Ordered one small coffee. The receipt kept going.",
        description=(
            "Deb wants one small coffee. Brent rings up the cup, the lid, the sleeve and the service, and the "
            "service is him reading the fees. Then she asks about the last line.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb) and Brian (Brent), lip-synced to "
            "their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica and Brian. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#hiddenfees", "#coffee", "#customerservice", "#prices", "#relatable", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("One small\ncoffee, please.", 0.5, "Collage 16", (600, 1000), 1.3, place="bottom"),
    ),
    tags=Tags(
        "money-services", "institution", "recognition", recurring=("deb", "brent"), test="sp-hook_motion", arm="a"
    ),
)
