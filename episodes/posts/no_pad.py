"""The release of no-pad."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "no-pad",
    InstagramPost(
        title="Why won't the waiter write it down?",
        description=(
            "He remembers everything. As always.\nA Collage sketch on Okayville, voiced with ElevenLabs premade "
            "voices Chris (Gary), Sarah (Priya) and Will (Jun); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, Sarah and Will. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#restaurant', '#waiter', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("He remembers everything", 21.5, number=208),
    ),
    tags=Tags("money-services", "other-person", "tension", test="sp-speakers", arm="b"),
    style="Collage",
    parts={
        "collage-arm": 1,
        "collage-cafe": 1,
        "collage-gary": 1,
        "collage-jun": 1,
        "collage-priya": 1,
        "collage-sign": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=17, reviewer=18),
    cover=True,
)
