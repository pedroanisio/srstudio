"""The release of firm-handshake."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "firm-handshake",
    InstagramPost(
        title="Did your parents tell you to just walk in?",
        description=(
            "He was out for forty minutes.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices "
            "Brian (Dad) and Matilda (Fern); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Matilda. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobsearch', '#parents', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Dad knows how jobs work", 10.2, number=193),
    ),
    tags=Tags("job-hunting", "other-person", "triumph", test="sp-speakers", arm="a"),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-frog": 2,
        "toon-goat": 1,
        "toon-hallway": 1,
        "toon-key-line": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
    },
    comedy=Scores(author=17, reviewer=18),
    cover=True,
)
