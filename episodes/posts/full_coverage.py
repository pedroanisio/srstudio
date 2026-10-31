"""The release of full-coverage."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "full-coverage",
    InstagramPost(
        title="I was told about the seagull.",
        description=(
            "What seagull?\n"
            "A Toon sketch voiced with ElevenLabs premade voices Brian (the agent) and Bill (the customer); every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Bill. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#rentalcar", "#travel", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("What seagull?", 15.0, "Toon"),
    ),
    tags=Tags("money-services", "institution", "tension", test="sp-hook_motion", arm="b"),
    style="Toon",
    comedy=Scores(author=16, reviewer=16),
    parts={
        # toon-gull-stare is drawn too and still proposed: a release cannot pin a proposed
        # version.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-clipboard": 1,
        "toon-counter": 1,
        "toon-goat": 1,
        "toon-gull": 1,
        "toon-ledge": 1,
        "toon-side-car": 1,
        "toon-yard": 1,
    },
)
