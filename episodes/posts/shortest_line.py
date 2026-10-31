"""The release of shortest-line."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "shortest-line",
    InstagramPost(
        title="Why is the line you pick always the slowest?",
        description=(
            "She's seventy-nine. She has nowhere to be."
            "\n"
            "A Cutout sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Lily (Rosa) and Liam (Milo). Foley synthesized.",
        hashtags=("#checkout", "#supermarket", "#relatable", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("Why is your line\nalways the slowest?", 5.4, "Okayville"),
    ),
    cover=True,
    tags=Tags(
        "money-services",
        "other-person",
        "tension",
        recurring=("milo", "rosa"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Cutout",
    parts={
        "captions": 1,
        "checkout-lane": 1,
        "customer": 1,
        "hand-basket": 1,
        "rosa": 1,
        "shop-till": 1,
        "shopping-cart": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(18, 18),
)
