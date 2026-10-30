"""The release of its-listening."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "its-listening",
    InstagramPost(
        title="We said mattress once. In bed. Now my phone is all mattresses.",
        description=(
            "Bruno and Mae said they need a new mattress, once, in bed. Now his phone is all mattress ads. It's "
            "listening, so Bruno tries to confuse it. It thanks him.\n"
            "A Toon sketch with Bruno and Mae, voiced with ElevenLabs premade voices Bill and Sarah; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Bill (Bruno) and Sarah (Mae). Buzz and sting synthesised.",
        hashtags=(
            "#targetedads",
            "#myphoneislistening",
            "#privacy",
            "#techhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("We said it once.\nIn bed.", 0.5, "Toon 22"),
    ),
    tags=Tags(
        "everyday-tech", "institution", "embarrassment", recurring=("bruno", "mae"), test="sp-hook_motion", arm="a"
    ),
    characters={"toon-bear": 1, "toon-rabbit": 1},
)
