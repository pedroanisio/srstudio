"""The release of the-noise."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-noise",
    InstagramPost(
        title="What kind of noise?",
        description=(
            "What's cheaper than a rattle?\n"
            "A Toon sketch voiced with ElevenLabs premade voices Liam (Fox) and Roger (the mechanic); every character "
            "is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam and Roger. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#carrepair", "#mechanic", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Do the noise.", 8.0, "Toon"),
    ),
    tags=Tags("money-services", "protagonist", "embarrassment", test="sp-hook_motion", arm="b"),
    style="Toon",
    comedy=Scores(author=19, reviewer=18),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-clipboard": 1,
        "toon-fox": 2,
        "toon-goat": 1,
        "toon-loose-wheel": 1,
        "toon-side-car": 1,
        "toon-yard": 1,
    },
)
