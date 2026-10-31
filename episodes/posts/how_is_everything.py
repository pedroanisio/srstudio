"""The release of how-is-everything."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "how-is-everything",
    InstagramPost(
        title="How does the waiter always know?",
        description=(
            "The only time they ask is with your mouth full."
            "\n"
            "A Cutout sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Liam (Milo) and Jessica (Ava). Foley synthesized.",
        hashtags=("#restaurant", "#waiter", "#relatable", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("How is\neverything?", 5.6, "Okayville"),
    ),
    cover=True,
    tags=Tags(
        "money-services",
        "institution",
        "triumph",
        recurring=("milo", "ava"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Cutout",
    parts={
        "barista": 1,
        "bean-jar": 1,
        "cafe": 1,
        "cafe-window": 1,
        "captions": 1,
        "customer": 1,
        "espresso-machine": 1,
        "menu-board": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(18, 19),
)
