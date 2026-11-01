"""The release of trial-shift."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "trial-shift",
    InstagramPost(
        title="Has anyone you know been hired after a trial shift?",
        description=(
            "Milo asks how long she's worked here. It's a quick trial shift, she says. It started in April, 2019.\nA "
            "Cutout sketch on Okayville, voiced with ElevenLabs premade voices Liam (Milo), Jessica (Ava) and Will "
            "(the Candidate); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam, Jessica and Will. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#jobhunting", "#firstjob", "#relatable", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Quick trial shift", 7.0, number=207),
    ),
    tags=Tags(
        "job-hunting", "institution", "tension", recurring=("milo", "ava", "candidate"), test="sp-speakers", arm="b"
    ),
    style="Cutout",
    parts={
        "barista": 1,
        "bean-jar": 1,
        "cafe": 1,
        "cafe-door": 1,
        "cafe-window": 1,
        "candidate": 1,
        "captions": 1,
        "coffee-cup": 1,
        "customer": 1,
        "cv-folder": 1,
        "espresso-machine": 1,
        "menu-board": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "reaching-hand": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
