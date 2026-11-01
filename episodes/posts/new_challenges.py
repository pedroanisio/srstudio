"""The release of new-challenges."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "new-challenges",
    InstagramPost(
        title="Why did you really leave your last job?",
        description=(
            "Left on good terms, through a window.\nA Toon sketch on Okayville, voiced with ElevenLabs premade "
            "voices Jessica (Dana) and Chris (Gil); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica and Chris. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#jobsearch', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("He left through a window", 16.4, number=213),
    ),
    tags=Tags("job-hunting", "protagonist", "triumph", test="sp-speakers", arm="a"),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dog": 2,
        "toon-finger": 1,
        "toon-frog": 2,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-room": 1,
    },
    comedy=Scores(author=17, reviewer=17),
    cover=True,
)
