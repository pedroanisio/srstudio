"""The release of the-last-guy."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-last-guy",
    InstagramPost(
        title="Who did this to you?",
        description=(
            "Every plumber is appalled by the last guy's work. It is never their own."
            "\n"
            "A Toon sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Charlie (Rex) and Matilda (Fern). Foley synthesised.",
        hashtags=('#plumber', '#homerepair', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Who did this?", 2.0, "Toon 30"),
    ),
    tags=Tags(
        "money-services",
        "other-person",
        "recognition",
        recurring=("rex", "fern"),
        test="sp-hook_motion",
        arm="a",
        recipient="a",
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dog": 2,
        "toon-frog": 2,
        "toon-key-line": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
    },
    comedy=Scores(18, 18),
)
