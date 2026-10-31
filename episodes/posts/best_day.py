"""The release of best-day."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "best-day",
    InstagramPost(
        title="Why does nobody ever tell you?",
        description=(
            "Nobody told you. Everyone saw."
            "\n"
            "A Collage sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Jessica (Deb). Foley synthesized.",
        hashtags=('#foodinteeth', '#embarrassing', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Today,\nI am magnetic.", 0.6, "Collage 34"),
    ),
    tags=Tags(
        "own-worst-enemy",
        "other-person",
        "triumph",
        recurring=("deb", "brent", "gary"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Collage",
    parts={
        "collage-bathroom": 1,
        "collage-boardroom": 1,
        "collage-brent": 1,
        "collage-bus-stop": 1,
        "collage-deb": 1,
        "collage-gary": 1,
        "collage-sign": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(17, 18),
)
