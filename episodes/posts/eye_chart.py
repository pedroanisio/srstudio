"""The release of eye-chart."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "eye-chart",
    InstagramPost(
        title="Better with one, or two?",
        description=(
            "The bottom line was always the hard one to read."
            "\n"
            "A Collage sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Jessica (Deb) and Alice (Dr. Feld). Foley synthesized.",
        hashtags=('#eyeexam', '#adulting', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Better with one,\nor two?", 0.5, "Collage 31"),
    ),
    tags=Tags(
        "money-services", "other-person", "relief", recurring=("deb",), test="sp-hook_motion", arm="a", recipient="a"
    ),
    style="Collage",
    parts={
        "collage-deb": 1,
        "collage-feld": 1,
        "collage-sign": 1,
        "collage-therapy": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(18, 19),
)
