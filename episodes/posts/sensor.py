"""The release of sensor."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "sensor",
    InstagramPost(
        title="Why do automatic taps ignore you?",
        description=(
            "Some people the sensor sees. Some people it never will."
            "\n"
            "A Collage sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will (Jun) and Daniel (Omar). Foley synthesised.",
        hashtags=('#sensor', '#publicrestroom', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Hello?\nI'm right here.", 1.4, "Collage 32"),
    ),
    tags=Tags(
        "everyday-tech",
        "institution",
        "tension",
        recurring=("jun", "omar", "kai"),
        test="sp-hook_motion",
        arm="a",
        recipient="a",
    ),
    style="Collage",
    parts={
        "collage-arm": 1,
        "collage-bathroom": 1,
        "collage-gust": 1,
        "collage-jun": 1,
        "collage-kai": 1,
        "collage-omar": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(18, 19),
)
