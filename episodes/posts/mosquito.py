"""The release of mosquito."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "mosquito",
    InstagramPost(
        title="Who else has lost a night to one mosquito?",
        description=(
            "One mosquito, two in the morning, and a grown adult with a rolled towel."
            "\n"
            "A Toon sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Bill (Bruno) and Sarah (Mae). Foley synthesised.",
        hashtags=('#mosquito', '#insomnia', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("It's in here.", 0.6, "Toon 31"),
    ),
    tags=Tags(
        "relationships",
        "protagonist",
        "tension",
        recurring=("bruno", "mae"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="partner",
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-bedroom": 1,
        "toon-captions": 1,
        "toon-key-line": 1,
        "toon-paw": 1,
        "toon-quilt": 1,
        "toon-rabbit": 2,
    },
    comedy=Scores(19, 18),
)
