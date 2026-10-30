"""The release of five-years."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

from ._interview import SERIES, VOICES

RELEASE = Release(
    "five-years",
    InstagramPost(
        title="Where do you see yourself in five years?",
        description=(
            "Episode 06 of The Interview. The candidate has a plan. It does not involve the job. It does involve the "
            "chair, which squeaks, and which gets taken for a spin before the credits."
        ),
        credit=VOICES + " Sound effects generated with ElevenLabs.",
        hashtags=SERIES + ("#fiveyearplan", "#executivechair"),
        thumbnail=Thumbnail("Where do you see\nyourself in 5 years?", 10.4, "The Interview · 06", (540, 560), 1.2),
    ),
    parts={
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "chair-back": 1,
        "episode-slate": 1,
        "laptop": 1,
        "manager": 1,
        "office-art": 1,
        "office-desk": 1,
        "office-reverse": 1,
        "office-wide": 1,
        "papers": 1,
        "plant": 1,
        "scorecard": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "squeak-mark": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
)
