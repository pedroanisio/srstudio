"""The release of the-scale."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-scale",
    InstagramPost(
        title="How much does a watch weigh?",
        description=(
            "Every pound you can take off in the waiting room counts."
            "\n"
            "A Collage sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Chris (Gary) and Sarah (Priya). Foley synthesized.",
        hashtags=('#doctorvisit', '#weighin', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Hop on.", 8.9, "Collage 35"),
    ),
    tags=Tags(
        "own-worst-enemy",
        "protagonist",
        "embarrassment",
        recurring=("gary", "priya"),
        test="sp-hook_motion",
        arm="a",
        recipient="a",
    ),
    style="Collage",
    parts={
        "collage-gary": 1,
        "collage-priya": 1,
        "collage-sign": 1,
        "collage-therapy": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(18, 18),
)
