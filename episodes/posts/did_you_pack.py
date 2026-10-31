"""The release of did-you-pack."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "did-you-pack",
    InstagramPost(
        title="Did you pack this bag yourself?",
        description=(
            "She has never once believed you are full."
            "\n"
            "A Stick sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Lily (Grandma), Will (Dev) and Eric (the officer). Foley synthesized."
        ),
        hashtags=('#grandma', '#airport', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("You look thin.", 2.0, "Stick"),
    ),
    cover=True,
    tags=Tags(
        "family",
        "other-person",
        "affection",
        recurring=("dev",),
        test="sp-hook_motion",
        arm="a",
        recipient="b",
        to="family",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-carry-on": 1,
        "stick-foil-note": 1,
        "stick-foil-parcel": 1,
        "stick-gate": 1,
        "stick-home-street": 1,
        "stick-kitchen": 1,
        "stick-plate": 1,
        "stick-poster": 1,
        "stick-rig": 1,
        "stick-robe": 1,
        "stick-scan-belt": 1,
        "stick-spoon": 1,
        "stick-table": 1,
        "stick-words": 1,
        "stick-xray": 1,
    },
    comedy=Scores(17, 19),
)
