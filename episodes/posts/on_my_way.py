"""The release of on-my-way."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "on-my-way",
    InstagramPost(
        title="On the bus, five minutes away. The map has other ideas.",
        description=(
            "Pip has waited forty minutes. Gil is on the bus, five minutes away. The map says he is at home, then in "
            "the bathroom. The map is very good. Then Gil checks his own map.\n"
            "A Toon sketch with Pip and Gil, voiced with ElevenLabs premade voices Alice and Chris; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice (Pip) and Chris (Gil). Sting synthesised.",
        hashtags=(
            "#runninglate",
            "#locationsharing",
            "#onmyway",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Where are you?\nOn the bus!", 0.5, "Toon 20"),
    ),
    tags=Tags("everyday-tech", "other-person", "recognition", recurring=("pip", "gil"), test="sp-hook_motion", arm="a"),
    characters={"toon-frog": 1, "toon-rabbit": 1},
)
