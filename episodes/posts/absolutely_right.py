"""The release of absolutely-right."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "absolutely-right",
    InstagramPost(
        title="Did it tell you that you were right, too?",
        description=(
            "Now both sides of every fight have a brilliant, supportive advisor.\nA Toon sketch on Okayville, "
            "voiced with ElevenLabs premade voices River (Mia) and Roger (Brock); every character is original, "
            "drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices River and Roger. Original characters, drawn in code. Sound effects"
            " synthesized in code."
        ),
        hashtags=('#chatbot', '#relationships', '#couples', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Day three of the fight", 25.5, number=211, focus=(570.0, 1920.0), zoom=1.06),
    ),
    tags=Tags("everyday-tech", "other-person", "embarrassment", test="sp-speakers", arm="a"),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-lounge": 1,
        "toon-rabbit": 2,
        "toon-speaker": 1,
    },
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
