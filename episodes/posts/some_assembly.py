"""The release of some-assembly."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "some-assembly",
    InstagramPost(
        title="Has flat-pack furniture ever nearly ended a relationship?",
        description=(
            "Four screws left over and a review of the relationship."
            "\n"
            "A Stick sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Jessica (Noor) and Will (Dev). Foley synthesized.",
        hashtags=('#flatpack', '#couples', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Step nine.", 11.5, "Stick 24"),
    ),
    cover=True,
    tags=Tags(
        "relationships",
        "institution",
        "tension",
        recurring=("noor", "dev"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="partner",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-book": 1,
        "stick-caller": 1,
        "stick-card": 1,
        "stick-drill": 1,
        "stick-manual-page": 1,
        "stick-planks": 1,
        "stick-rig": 1,
        "stick-screws": 1,
        "stick-studio-flat": 1,
        "stick-wardrobe": 1,
        "stick-words": 1,
    },
    comedy=Scores(18, 18),
)
