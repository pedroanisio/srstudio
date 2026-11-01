"""The release of still-on."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "still-on",
    InstagramPost(
        title="Who cancels first?",
        description=(
            "Neither of them. That is the whole friendship.\nA Soft sketch on Okayville, voiced with ElevenLabs "
            "premade voices Laura (Juno) and Alice (Pip); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Laura and Alice. Original characters, drawn in code. Sound effects"
            " synthesized in code."
        ),
        hashtags=('#friendship', '#canceledplans', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Four slippers", 17.8, number=216),
    ),
    tags=Tags("relationships", "protagonist", "relief", test="sp-speakers", arm="a"),
    style="Soft",
    parts={},
    comedy=Scores(author=15, reviewer=18),
    cover=True,
)
