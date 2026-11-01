"""The release of two-weeks."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "two-weeks",
    InstagramPost(
        title="How long is two weeks in contractor?",
        description=(
            "The hole never changes. Everything else does.\nA Collage sketch on Okayville, voiced with ElevenLabs "
            "premade voices Daniel (Omar), Chris (Gary) and Jessica (Deb); every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Daniel, Chris and Jessica. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#contractor', '#homerenovation', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("It's been two weeks", 16.2, number=212),
    ),
    tags=Tags("money-services", "other-person", "recognition", test="sp-speakers", arm="b"),
    style="Collage",
    parts={},
    comedy=Scores(author=16, reviewer=18),
    cover=True,
)
