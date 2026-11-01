"""The release of someone-else."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "someone-else",
    InstagramPost(
        title="Is there someone else?",
        description=(
            "Eleven years. Is it fiber?\n"
            "A Toon sketch voiced with ElevenLabs premade voices Sarah (the caller) and River (the agent); every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah and River. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#internet", "#customerservice", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Is it fiber?", 8.0, "Toon"),
    ),
    tags=Tags("money-services", "institution", "recognition", test="sp-hook_motion", arm="b"),
    style="Toon",
    comedy=Scores(author=18, reviewer=19),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-call-centre": 1,
        "toon-captions": 1,
        "toon-clipboard": 1,
        "toon-dog": 2,
        "toon-eye-drops": 1,
        "toon-fox": 2,
        "toon-frog": 2,
        "toon-headset": 1,
        "toon-hedgehog": 2,
        "toon-home": 1,
        "toon-ledge": 1,
        "toon-phone": 1,
        "toon-rabbit": 2,
        "toon-raccoon": 2,
    },
)
