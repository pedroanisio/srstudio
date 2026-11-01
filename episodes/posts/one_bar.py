"""The release of one-bar."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "one-bar",
    InstagramPost(
        title="Where is the one good spot in your house?",
        description=(
            "Every home has one square foot of signal, and it is always somewhere a person cannot stand.\nA Toon "
            "sketch on Okayville, voiced with ElevenLabs premade voices Chris (Gil) and River (Mia); every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris and River. Original characters, drawn in code. Sound effects"
            " synthesized in code."
        ),
        hashtags=('#nosignal', '#wifi', '#homelife', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("One bar. Don't move.", 7.1, number=210, focus=(540.0, 1920.0), zoom=1.02),
    ),
    tags=Tags("everyday-tech", "institution", "tension", test="sp-speakers", arm="a"),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-frog": 2,
        "toon-hallway": 1,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-rabbit": 2,
    },
    comedy=Scores(author=15, reviewer=18),
    cover=True,
)
