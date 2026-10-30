"""The release of the-stove."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-stove",
    InstagramPost(
        title="Did you turn off the stove?",
        description=(
            "You did. You know you did. You remember doing it. Anyway, turn the car around.\n"
            "Stick 13: one car, one street, every holiday you never took, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will and Jessica. Sound effects with ElevenLabs.",
        hashtags=("#couples", "#anxiety", "#roadtrip", "#marriage", "#stickfigure", "#animatedshorts"),
        thumbnail=Thumbnail("Did you\nturn off\nthe stove?", 0.5, "Stick 13", (540, 860), 1.0, place="top"),
    ),
    cover=True,
    tags=Tags(
        "relationships",
        "protagonist",
        "tension",
        recurring=("dev", "noor"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="partner",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-rig": 1,
        "stick-windshield": 1,
        "stick-windshield-dash": 1,
        "stick-words": 1,
    },
)
