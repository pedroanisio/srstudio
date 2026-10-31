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
        # soft-bowling-ball is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-brick is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-coin-bag is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-dimmer is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-dust is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-home-fridge is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-smoke is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-tv is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-washer is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-home": 1,
        "soft-shovel": 1,
        "soft-sofa": 1,
        "soft-time-card": 1,
    },
    comedy=Scores(18, 18),
)
