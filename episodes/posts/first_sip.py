"""The release of first-sip."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "first-sip",
    InstagramPost(
        title="Can anyone actually taste the difference?",
        description=(
            "Say something about the finish and hope nobody asks."
            "\n"
            "A Collage sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Brian (Brent), Jessica (Deb) and Daniel (Omar). Foley synthesized.",
        hashtags=('#winetasting', '#dinnerdate', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Bold.", 6.0, "Collage 33"),
    ),
    tags=Tags(
        "relationships",
        "protagonist",
        "embarrassment",
        recurring=("brent", "deb", "omar"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="partner",
    ),
    style="Collage",
    parts={
        "collage-brent": 1,
        "collage-cafe": 1,
        "collage-deb": 1,
        "collage-omar": 1,
        "collage-tablecloth": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(18, 18),
)
