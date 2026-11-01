"""The release of no-thanks."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "no-thanks",
    InstagramPost(
        title="Ten business days",
        description=(
            "Ever had to insult yourself to say no?\n"
            "A Collage sketch voiced with ElevenLabs premade voices Brian (Brent) and Sarah (Priya), lip-synced to "
            "their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Sarah. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#unsubscribe", "#onlineshopping", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("No thanks.", 2.6, "Collage"),
    ),
    tags=Tags("everyday-tech", "institution", "tension", recurring=("brent", "priya"), test="sp-hook_motion", arm="b"),
    style="Collage",
    comedy=Scores(author=19, reviewer=18),
    parts={
        "collage-bedroom": 1,
        "collage-brent": 1,
        "collage-duvet": 1,
        "collage-flip-card": 1,
        "collage-priya": 1,
        "collage-supermarket": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
