"""The release of multitasking."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

from ._interview import SERIES, VOICES

RELEASE = Release(
    "multitasking",
    InstagramPost(
        title="Are you good at multitasking? Absolutely.",
        description=(
            "Episode 04 of The Interview. Asked for an example, the candidate names the one task they can run in "
            "parallel without dropping anything. Status pings included."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#multitasking", "#disappointment"),
        thumbnail=Thumbnail("Good at\nmultitasking?", 5.0, "The Interview · 04", (540, 520), 1.1),
    ),
    parts={
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "dashboard": 1,
        "episode-slate": 1,
        "laptop": 1,
        "manager": 1,
        "notification": 1,
        "office-art": 1,
        "office-reverse": 1,
        "office-wide": 1,
        "papers": 1,
        "plant": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
)
