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
)
