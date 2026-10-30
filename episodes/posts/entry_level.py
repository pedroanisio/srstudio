"""The release of entry-level."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "entry-level",
    InstagramPost(
        title="Entry level. Ten years' experience. Nobody has started early enough.",
        description=(
            "The ad is very clear about the experience it wants, and the applicants keep getting younger to meet it.\n"
            "The role has been filled for some time."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Eric, Will, Liam, Brian and George. Sound effects generated with "
            "ElevenLabs."
        ),
        hashtags=("#jobhunting", "#interview", "#careers", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("Entry level.\n10 years' experience.", 0.5, "Now hiring"),
    ),
    cover=True,
    tags=Tags(
        "job-hunting", "institution", "tension", recurring=("rosa",), test="sp-hook_motion", arm="a", recipient="a"
    ),  # fmt: skip
    style="Cutout",
    parts={
        "candidate": 1,
        "captions": 1,
        "chair": 1,
        "coffee-cup": 1,
        "customer": 1,
        "manager": 1,
        "office-reverse": 1,
        "papers": 1,
        "rosa": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
)
