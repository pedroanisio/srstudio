"""The release of since-i-was-six."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "since-i-was-six",
    InstagramPost(
        title="Why do you really want to work here?",
        description=(
            "Thirty years in grout.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Charlie "
            "(Rex) and Matilda (Fern); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Charlie and Matilda. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#jobsearch', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("A passion for grout", 24.8, number=201),
    ),
    tags=Tags("job-hunting", "protagonist", "affection", test="sp-speakers", arm="a"),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dog": 2,
        "toon-finger": 1,
        "toon-frog": 2,
        "toon-ledge": 1,
        "toon-room": 1,
    },
    comedy=Scores(author=17, reviewer=17),
    cover=True,
)
