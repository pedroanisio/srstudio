"""The release of warranty."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "warranty",
    InstagramPost(
        title="Why does it always die the day after?",
        description=(
            "Every appliance knows the date its warranty ends, and this one has until midnight."
            "\n"
            "A Soft sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will (Pip) and Laura (Juno). Foley synthesized.",
        hashtags=("#okayville", "#warranty", "#homeowner", "#appliances", "#animatedcomedy"),
        thumbnail=Thumbnail("Same\nday.", 24.6, "The warranty", place="top"),
    ),
    tags=Tags(
        "money-services",
        "institution",
        "tension",
        recurring=("pip", "juno"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Soft",
    parts={
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-bowling-ball": 1,
        "soft-brick": 1,
        "soft-coin-bag": 1,
        "soft-dust": 1,
        "soft-home": 1,
        "soft-home-fridge": 1,
        "soft-shovel": 1,
        "soft-smoke": 1,
        "soft-sofa": 1,
        "soft-time-card": 1,
        "soft-tv": 1,
        "soft-washer": 1,
    },
    comedy=Scores(18, 18),
)
