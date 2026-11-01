"""The release of the-drawer."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "the-drawer",
    InstagramPost(
        title="What is that cable even for?",
        description=(
            "Every home has one drawer nobody is allowed to win an argument about.\nA Toon sketch on Okayville, "
            "voiced with ElevenLabs premade voices Bill (Bruno) and Sarah (Mae); every character is original, "
            "drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Bill and Sarah. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#cables', '#junkdrawer', '#homelife', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Nobody knows what it's for", 10.3, number=204),
    ),
    tags=Tags("everyday-tech", "protagonist", "tension", test="sp-speakers", arm="a"),
    style="Toon",
    parts={},
    comedy=Scores(author=16, reviewer=19),
    cover=True,
)
