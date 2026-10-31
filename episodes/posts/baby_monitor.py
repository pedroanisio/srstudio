"""The release of baby-monitor."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "baby-monitor",
    InstagramPost(
        title="Can your guests hear you in the kitchen?",
        description=(
            "Mae and Bruno keep their voices down. It is a very good "
            "monitor.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Sarah (Mae), Bill (Bruno)"
            " and Laura (his mother); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah, Bill and Laura. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#dinnerparty', '#inlaws', '#marriagehumor', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("It tastes like\na wet ceiling.", 7.6, "Okayville"),
    ),
    tags=Tags(
        "relationships", "protagonist", "embarrassment", recurring=('mae', 'bruno'), test="sp-hook_motion", arm="b"
    ),
    style="Toon",
    parts={
        # toon-baby-monitor, toon-lasagna, toon-monitor-receiver, toon-swing-door also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-dog": 2,
        "toon-goat": 1,
        "toon-hedgehog": 2,
        "toon-home": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-rabbit": 2,
        "toon-table": 1,
    },
    comedy=Scores(author=16, reviewer=18),
)
