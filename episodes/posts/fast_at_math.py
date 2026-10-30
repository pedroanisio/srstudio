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
    characters={"candidate": 1, "manager": 1},
)
