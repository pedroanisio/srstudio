"""The release of just-a-trim."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "just-a-trim",
    InstagramPost(
        title="Just a trim, please. There was a lawnmower in the room. She said nothing.",
        description=(
            "Nobody has ever told a barber the truth while still wearing the cape.\nRosa, from the elevator, loving it."
        ),
        credit="Voices: ElevenLabs premade voices Lily and Jessica. Sound effects generated with ElevenLabs.",
        hashtags=("#haircut", "#barber", "#everydaylife", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("Just a trim,\nplease.", 0.5, "How's that?"),
    ),
    cover=True,
    tags=Tags(
        "money-services",
        "protagonist",
        "embarrassment",
        recurring=("rosa",),
        test="sp-hook_motion",
        arm="a",
        recipient="a",
    ),  # fmt: skip
    style="Cutout",
    parts={
        "barista": 1,
        "captions": 1,
        "card-reader": 1,
        "manager": 1,
        "rosa": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
