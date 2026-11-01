"""The release of round-seven."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "round-seven",
    InstagramPost(
        title="How many interview rounds is too many?",
        description=(
            "Twelve years on the wall and still not hired.\nA Cutout sketch on Okayville, voiced with ElevenLabs "
            "premade voices Jessica (Ava), Will (the Candidate) and Eric (the Boss); every character is original,"
            " drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, Will and Eric. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobsearch', '#interview', '#jobhunting', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Another interview", 14.6, number=203),
    ),
    tags=Tags("job-hunting", "institution", "recognition", test="sp-speakers", arm="b"),
    style="Cutout",
    parts={
        "barista": 1,
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "coffee-cup": 1,
        "globe-pendant": 1,
        "hiring-office": 1,
        "manager": 1,
        "office-reverse": 1,
        "papers": 1,
        "reception": 1,
        "reception-counter": 1,
        "roller-blind": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "slat-wall": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
    comedy=Scores(author=16, reviewer=16),
    cover=True,
)
