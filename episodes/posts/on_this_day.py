"""The release of on-this-day."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "on-this-day",
    InstagramPost(
        title="Who asked your phone to do that?",
        description=(
            "He fixed her sink.\nA Collage sketch on Okayville, voiced with ElevenLabs premade voices Sarah "
            "(Priya), Will (Jun) and Matilda (Rosa); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah, Will and Matilda. Original characters, drawn in code. Sound"
            " effects synthesized in code."
        ),
        hashtags=('#relationships', '#exes', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Your phone made a film", 15.9, number=194),
    ),
    tags=Tags("everyday-tech", "institution", "embarrassment", test="sp-speakers", arm="b"),
    style="Collage",
    parts={},
    comedy=Scores(author=16, reviewer=19),
    cover=True,
)
