"""The release of pressure-interview."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

from ._interview import SERIES, VOICES

RELEASE = Release(
    "pressure-interview",
    InstagramPost(
        title="How do you handle pressure?",
        description=(
            "Episode 02 of The Interview. A perfectly honest answer about pressure, and a manager who realises too "
            "late that they were talking about the same thing."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#notifications", "#worklifebalance"),
        thumbnail=Thumbnail("How do you handle\npressure?", 6.0, "The Interview · 02", (540, 700), 1.4),
    ),
    parts={
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "laptop": 1,
        "manager": 1,
        "office-art": 1,
        "office-reverse": 1,
        "office-wide": 1,
        "papers": 1,
        "plant": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "silent-phone": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
)
