"""The release of who-names."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "who-names",
    InstagramPost(
        title="What do you say on the drive home?",
        description=(
            "The review of the dinner party only works if the call has really ended.\nA Toon sketch on Okayville, "
            "voiced with ElevenLabs premade voices Daniel (Otto), Sarah (Mae) and Jessica (Dana); every character"
            " is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Daniel, Sarah and Jessica. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#dinnerparty', '#couples', '#drivehome', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Leaving the dinner party", 19.5, number=202),
    ),
    tags=Tags("relationships", "protagonist", "embarrassment", test="sp-speakers", arm="b"),
    style="Toon",
    parts={},
    comedy=Scores(author=17, reviewer=18),
    cover=True,
)
