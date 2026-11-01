"""The release of following-up."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "following-up",
    InstagramPost(
        title="How long did your last email take?",
        description=(
            "Four hours and two friends for one line.\nA Toon sketch on Okayville, voiced with ElevenLabs premade "
            "voices River (Mia), Daniel (Otto) and Will (Lewis); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices River, Daniel and Will. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#jobsearch', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Four hours on one email", 29.3, number=209),
    ),
    tags=Tags("job-hunting", "protagonist", "recognition", test="sp-speakers", arm="b"),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-clock": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-mug": 1,
        "toon-rabbit": 2,
        "toon-raccoon": 2,
    },
    comedy=Scores(author=15, reviewer=17),
    cover=True,
)
