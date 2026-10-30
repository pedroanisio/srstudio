"""The release of honesty-interview."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

from ._interview import SERIES, VOICES

RELEASE = Release(
    "honesty-interview",
    InstagramPost(
        title="Greatest weakness? Honesty.",
        description=(
            "Episode 01 of The Interview. The candidate is asked for a weakness and gives the one answer the manager "
            "cannot argue with, twice.\n"
            "Contains one strong word."
        ),
        credit=VOICES,
        hashtags=SERIES + ("#honesty", "#interviewfail"),
        thumbnail=Thumbnail("Greatest weakness?\nHonesty.", 2.4, "The Interview · 01", (540, 690), 1.4),
    ),
    video="honesty-interview-recreated",
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
        "water-glass": 1,
        "woodgrain": 1,
    },
)
