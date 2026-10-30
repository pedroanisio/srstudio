"""The release of day-off."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "day-off",
    InstagramPost(
        title="Saturday. No work. Just me.",
        description=(
            "Pip finally has a day off. His hands keep typing on nothing, he agrees with the lamp, and he can stop "
            "any time. The only way he can rest is to book it: a meeting with the sofa.\n"
            "Episode 11, the fourth in the Soft style: every pose lands on the beat."
        ),
        credit=(
            "Pip: ElevenLabs premade voice Will. Music composed with ElevenLabs Music. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#dayoff",
            "#weekendvibes",
            "#burnout",
            "#workaholic",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Day off?\nBook it.", 19.6, "Soft 04", (600, 1000), 1.25),
    ),
    parts={
        "captions": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-home": 1,
        "soft-sofa": 1,
        "soft-status-badge": 1,
    },
)
