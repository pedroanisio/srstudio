"""The release of bin-day."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "bin-day",
    InstagramPost(
        title="Who else has chased the trash truck in a robe?",
        description=(
            "You can hear the truck from bed. You will not make it."
            "\n"
            "A Stick sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George (Walt), Lily (Margaret), Bill (the driver) and Will (Dev). "
            "Foley synthesized."
        ),
        hashtags=('#trashday', '#neighbors', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Left it\nvery late", 4.0, "Stick 23"),
    ),
    cover=True,
    tags=Tags(
        "own-worst-enemy",
        "protagonist",
        "embarrassment",
        recurring=("dev",),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="roommate",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-home-street": 1,
        "stick-mug": 1,
        "stick-rig": 1,
        "stick-robe": 1,
        "stick-slipper": 1,
        "stick-sparks": 1,
        "stick-trash-truck": 1,
        "stick-wheelie-bin": 1,
        "stick-words": 1,
    },
    comedy=Scores(18, 18),
)
