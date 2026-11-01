"""The release of pajama-day."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "pajama-day",
    InstagramPost(
        title="Are you still in the class group chat?",
        description=(
            "Nobody knows if it's Thursday. Denise is typing.\nA Toon "
            "sketch on Okayville, voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno); every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah and Bill. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#groupchat', '#schoolparents', '#parenting', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Denise is\ntyping.", 18.5, "Okayville"),
    ),
    tags=Tags("family", "protagonist", "recognition", recurring=('mae', 'bruno'), test="sp-hook_motion", arm="b"),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-cupcakes": 1,
        "toon-hamster": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-phone": 1,
        "toon-rabbit": 2,
    },
    comedy=Scores(author=14, reviewer=18),
)
