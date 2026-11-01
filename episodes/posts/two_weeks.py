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
    parts={
        "collage-arm": 1,
        "collage-deb": 1,
        "collage-dining-room": 1,
        "collage-gary": 1,
        "collage-omar": 1,
        "collage-photo-print": 1,
        "collage-salt-shaker": 1,
        "collage-sign": 1,
        "collage-sofa": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=16, reviewer=18),
    cover=True,
)
