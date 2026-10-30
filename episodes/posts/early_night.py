"""The release of early-night."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "early-night",
    InstagramPost(
        title="Tonight: bed by ten",
        description=(
            "It is 3:47 and she now holds strong views on Bulgarian beekeeping.\nThe shovel looks great, though."
        ),
        credit="Voices: ElevenLabs premade voices Brian (narrator) and Laura (Juno). Foley synthesised.",
        hashtags=(
            "#insomnia",
            "#doomscrolling",
            "#bedtime",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Tonight:\nbed by ten.", 0.8, place="top"),
    ),
    style="Soft",
    # soft-bedroom, soft-hive, soft-phone, soft-shovel and soft-time-card join these at version 1
    # once the operator decides them: a release cannot pin a proposed version, so the pin check refuses this reel.
    tags=Tags(
        territory="everyday-tech",
        cause="protagonist",
        emotion="embarrassment",
        recurring=("juno",),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    parts={
        "bo": 1,
        "captions": 1,
        "juno": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-bedroom": 1,
        "soft-hive": 1,
        "soft-phone": 1,
        "soft-shovel": 1,
        "soft-time-card": 1,
    },
)
