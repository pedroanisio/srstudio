"""The release of smart-lamp."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "smart-lamp",
    InstagramPost(
        title="You never listen to me.",
        description=(
            "Juno says Pip never listens. He always listens! The smart lamp disagrees: it has recordings. Then it "
            "orders flowers, with a card that says sorry. Then a ring.\n"
            "Comedy Cut 17: Pip, Juno and Mister Lamp from Day Off, pose to pose on a 120 bpm beat."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno), Will (Pip) and Matilda (the lamp). Music composed with "
        "ElevenLabs Music. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#smarthome",
            "#relationshiphumor",
            "#couplegoals",
            "#techhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("The lamp\nhas recordings.", 6.0, "Episode 17", (540, 900), 1.0),
    ),
)
