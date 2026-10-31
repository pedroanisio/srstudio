"""The release of fitted-sheet."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "fitted-sheet",
    InstagramPost(
        title="How do you fold a fitted sheet?",
        description=(
            "Nobody has ever folded one. Nobody has ever said so out loud."
            "\n"
            "A Toon sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Sarah (Mae), Lily (her mother) and Bill (Bruno). Foley synthesised.",
        hashtags=('#fittedsheet', '#laundry', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Who sent you?", 19.6, "Toon 32"),
    ),
    tags=Tags(
        "family",
        "protagonist",
        "affection",
        recurring=("mae", "bruno"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="family",
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-closet": 1,
        "toon-hallway": 1,
        "toon-hedgehog": 2,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-paw": 1,
        "toon-rabbit": 2,
    },
    comedy=Scores(18, 19),
)
