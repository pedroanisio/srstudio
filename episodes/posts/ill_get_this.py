"""The release of ill-get-this."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "ill-get-this",
    InstagramPost(
        title="Whose money is no good here?",
        description=(
            "Gary and Omar have been fighting over this bill for eleven years. Rosa ordered dessert.\nA Collage "
            "sketch on Okayville, voiced with ElevenLabs premade voices Chris (Gary), Daniel (Omar), Will (Jun) "
            "and Matilda (Rosa); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, Daniel, Will and Matilda. Original characters, drawn in "
            "code. Sound effects synthesized in code."
        ),
        hashtags=('#splitthebill', '#family', '#dinner', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("I've got\nthis.", 0.6, "Okayville"),
    ),
    tags=Tags(
        "family", "other-person", "embarrassment", recurring=('gary', 'omar', 'rosa'), test="sp-hook_motion", arm="b"
    ),
    style="Collage",
    parts={
        # collage-bank-card, collage-counter, collage-receipt, collage-till, collage-tiny-cup, collage-wallet
        # also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "collage-arm": 1,
        "collage-cafe": 1,
        "collage-gary": 1,
        "collage-jun": 1,
        "collage-omar": 1,
        "collage-rosa": 1,
        "collage-tablecloth": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=14, reviewer=17),
)
