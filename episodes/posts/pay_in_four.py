"""The release of pay-in-four."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "pay-in-four",
    InstagramPost(
        title="Would you finance a burrito?",
        description=(
            "Four easy payments. She stopped at two.\nA Stick sketch on Okayville, voiced with ElevenLabs premade "
            "voices Jessica (Noor) and Callum (the repo man); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica and Callum. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#buynowpaylater', '#burrito', '#adulting', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("The burrito went to collections", 2.0, number=198),
    ),
    tags=Tags("money-services", "institution", "tension", recurring=('noor',), test="sp-speakers", arm="a"),
    style="Stick",
    parts={},
    comedy=Scores(author=17, reviewer=18),
    cover=True,
)
