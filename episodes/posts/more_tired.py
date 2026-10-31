"""The release of more-tired."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "more-tired",
    InstagramPost(
        title="Who slept less?",
        description=(
            "It is six in the morning and nobody is conceding. Then the baby wakes up, and so does the strategy.\n"
            "A Stick sketch on Okayville, voiced with ElevenLabs premade voices Jessica (Noor) and Will (Dev); every "
            "character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Jessica and Will. Original characters, drawn in code. Sound effects "
        "with ElevenLabs; the fridge door and the keys synthesized in code.",
        hashtags=("#newparents", "#parenting", "#marriagehumor", "#stickfigure", "#okayville"),
        thumbnail=Thumbnail("Resting\nloudly", 20.3, "Okayville", (510, 740), 1.3, place="top"),
    ),
    cover=True,
    tags=Tags(
        "relationships", "other-person", "recognition", recurring=("dev", "noor"), test="sp-hook_motion", arm="b"
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-fridge-open": 1,
        "stick-key": 1,
        "stick-kitchen": 1,
        "stick-mug": 1,
        "stick-rig": 1,
        "stick-table": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=15, reviewer=18),
)
