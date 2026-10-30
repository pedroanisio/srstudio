"""The release of my-machine."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "my-machine",
    InstagramPost(
        title="The site is down. Works on my machine. So they're shipping my machine.",
        description=(
            "The site is down, everyone is waiting, and it works on Rex's machine. Great idea, says Mia: she is "
            "shipping his machine to them. He fixes it in seconds. The courier comes anyway.\n"
            "A Toon sketch with Mia and Rex, voiced with ElevenLabs premade voices River and Charlie; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices River (Mia) and Charlie (Rex). Buzz and sting synthesised.",
        hashtags=(
            "#worksonmymachine",
            "#developerlife",
            "#programmerhumor",
            "#techsupport",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Works on\nmy machine.", 0.5, "Toon 23"),
    ),
    tags=Tags("office", "protagonist", "recognition", recurring=("mia", "rex"), test="sp-hook_motion", arm="b"),
)
