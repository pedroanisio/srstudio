"""The release of tell-us."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "tell-us",
    InstagramPost(
        title="Where do you start with \"tell us about yourself\"?",
        description=(
            "Gary started at birth.\nA Collage sketch on Okayville, voiced with ElevenLabs premade voices Brian "
            "(Brent), Jessica (Deb) and Chris (Gary); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian, Jessica and Chris. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#jobsearch', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("He started at birth", 12.0, number=199),
    ),
    tags=Tags("job-hunting", "protagonist", "embarrassment", test="sp-speakers", arm="b"),
    style="Collage",
    parts={
        "collage-boardroom": 1,
        "collage-brent": 1,
        "collage-deb": 1,
        "collage-gary": 1,
        "collage-sign": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
