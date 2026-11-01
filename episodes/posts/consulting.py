"""The release of consulting."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "consulting",
    InstagramPost(
        title="What is your resume gap really called?",
        description=(
            "One client. Very demanding.\nA Stick sketch on Okayville, voiced with ElevenLabs premade voices "
            "Jessica (Noor) and Will (Dev); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica and Will. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#resumegap', '#jobsearch', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Consulting for a couch", 4.0, number=205),
    ),
    tags=Tags("job-hunting", "protagonist", "relief", recurring=('dev', 'noor'), test="sp-speakers", arm="a"),
    style="Stick",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-rig": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=15, reviewer=16),
    cover=True,
)
