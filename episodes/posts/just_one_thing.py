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
        "coffee-cup": 1,
        "customer": 1,
        "plant": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
