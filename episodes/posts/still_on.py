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
        thumbnail=ShowCover("Both already in blankets", 2.0, number=216),
    ),
    tags=Tags("relationships", "protagonist", "relief", test="sp-speakers", arm="a"),
    style="Soft",
    parts={
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-phone": 1,
    },
    comedy=Scores(author=15, reviewer=18),
    cover=True,
)
