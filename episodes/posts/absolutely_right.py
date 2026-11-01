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
        thumbnail=ShowCover("Day three of the fight", 25.5, number=211),
    ),
    tags=Tags("everyday-tech", "other-person", "embarrassment", test="sp-speakers", arm="a"),
    style="Toon",
    parts={},
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
