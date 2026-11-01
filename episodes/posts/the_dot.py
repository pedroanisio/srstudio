"""The release of the-dot."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "the-dot",
    InstagramPost(
        title="Does your mother know where you are?",
        description=(
            "It was shampoo, and she has a pen.\nA Cutout sketch on Okayville, voiced with ElevenLabs premade "
            "voices Lily (Rosa), Liam (Milo) and Jessica (Ava); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Lily, Liam and Jessica. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#family', '#tech', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("First date", 13.8, number=214),
    ),
    tags=Tags("everyday-tech", "other-person", "embarrassment", test="sp-speakers", arm="b"),
    style="Cutout",
    parts={
        "barista": 1,
        "bean-jar": 1,
        "cafe": 1,
        "cafe-table": 1,
        "cafe-window": 1,
        "captions": 1,
        "customer": 1,
        "espresso-machine": 1,
        "menu-board": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "reaching-hand": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "taper-candles": 1,
    },
    comedy=Scores(author=16, reviewer=18),
    cover=True,
)
