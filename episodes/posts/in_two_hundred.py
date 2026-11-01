"""The release of in-two-hundred."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "in-two-hundred",
    InstagramPost(
        title="Who wins, the map or the passenger?",
        description=(
            "It has satellites. She grew up here.\nA Stick sketch on Okayville, voiced with ElevenLabs premade "
            "voices Will (Dev), Jessica (Noor) and Alice (the map); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will, Jessica and Alice. Original characters, drawn in code. Sound"
            " effects synthesized in code."
        ),
        hashtags=('#roadtrip', '#gps', '#marriage', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("The map took her side", 2.0, number=200),
    ),
    tags=Tags("everyday-tech", "protagonist", "triumph", recurring=('dev', 'noor'), test="sp-speakers", arm="b"),
    style="Stick",
    parts={},
    comedy=Scores(author=16, reviewer=18),
    cover=True,
)
