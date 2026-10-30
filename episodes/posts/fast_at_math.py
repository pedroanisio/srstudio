"""The release of fast-at-math."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

from ._interview import SERIES, VOICES

RELEASE = Release(
    "fast-at-math",
    InstagramPost(
        title="17 × 19? Forty-two. But it was fast.",
        description=(
            "Episode 03 of The Interview. Greatest strength: speed. Accuracy was not on the list. Hand gestures, a "
            "facepalm and a scorecard that keeps the receipts."
        ),
        credit=VOICES + " Original sound effects.",
        hashtags=SERIES + ("#mathjokes", "#fastnotright"),
        thumbnail=Thumbnail("17 × 19?\nForty-two.", 5.4, "The Interview · 03", (600, 520), 1.15),
    ),
    parts={
        "answer-bubble": 1,
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "episode-slate": 1,
        "laptop": 1,
        "manager": 1,
        "office-art": 1,
        "office-reverse": 1,
        "office-wide": 1,
        "papers": 1,
        "plant": 1,
        "quiz-card": 1,
        "scorecard": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
)
