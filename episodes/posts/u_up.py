"""The release of u-up."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "u-up",
    InstagramPost(
        title="I just texted my ex. Was that a mistake?",
        description=(
            "Two in the morning: u up? The router won't unsend it; it doesn't fail anymore, it has grown. She's "
            "typing: who is this? Then she remembers the forty dollars. The router has already paid them, with a "
            "memo.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Daniel."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#textingmyex",
            "#latenighttexts",
            "#datinghumor",
            "#techhumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("2 AM.\nTexting the ex.", 1.4, "Ink 05", (540, 420), 1.5),
    ),
    cover=True,
)
