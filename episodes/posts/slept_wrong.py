"""The release of slept-wrong."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "slept-wrong",
    InstagramPost(
        title="What's the stupidest way you've hurt your back?",
        description=(
            "There is an age when sleeping counts as an injury."
            "\n"
            "A Toon sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Brian, George and Liam. Foley synthesized.",
        hashtags=('#gettingold', '#backpain', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("I slept.", 17.0, "Toon"),
    ),
    tags=Tags(
        "own-worst-enemy", "protagonist", "recognition", test="sp-hook_motion", arm="a", recipient="b", to="best friend"
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dishes": 1,
        "toon-goat": 1,
        "toon-hamster": 1,
        "toon-key-line": 1,
        "toon-paw": 1,
        "toon-restaurant": 1,
        "toon-sloth": 1,
        "toon-table": 1,
    },
    comedy=Scores(18, 19),
)
