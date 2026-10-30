"""The release of just-one-thing."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "just-one-thing",
    InstagramPost(
        title="He went in for light bulbs. He owns a kayak now.",
        description=("The list had one thing on it. It is a very nice kayak.\nMilo, from the cafe, in the dark."),
        credit="Voice: ElevenLabs premade voice Liam. Sound effects generated with ElevenLabs.",
        hashtags=("#shopping", "#homelife", "#everydaylife", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("I only need\nlight bulbs.", 0.5, "It was on sale"),
    ),
    cover=True,
    tags=Tags(
        "money-services",
        "protagonist",
        "embarrassment",
        recurring=("milo",),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),  # fmt: skip
    style="Cutout",
    parts={
        "captions": 1,
        "card-reader": 1,
        "checkout-lane": 1,
        "coffee-cup": 1,
        "customer": 1,
        "dark-eyes": 1,
        "hand-basket": 1,
        "kayak": 1,
        "life-ring": 1,
        "light-switch": 1,
        "long-receipt": 1,
        "paddle": 1,
        "plant": 1,
        "shelf-goods": 1,
        "shopping-cart": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "step-ladder": 1,
        "store-aisle": 1,
        "table-lamp": 1,
        "taper-candles": 1,
    },
)
