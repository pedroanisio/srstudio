"""The release of take-my-phone."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "take-my-phone",
    InstagramPost(
        title="Do NOT let me text him.",
        description=(
            "Your only job was to hold the phone. She has been planning this since before she handed it to you.\n"
            "Stick 11: one kitchen, one fridge, one safe, one very small key, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Laura and Alice. Sound effects with ElevenLabs.",
        hashtags=("#exes", "#texting", "#bestfriends", "#relatable", "#stickfigure", "#animatedshorts"),
        thumbnail=Thumbnail("Do NOT\nlet me\ntext him.", 0.5, "Stick 11", (540, 860), 1.0, place="top"),
    ),
    cover=True,
    tags=Tags(
        "relationships", "protagonist", "triumph", test="sp-hook_motion", arm="a", recipient="b", to="best friend"
    ),
    style="Stick",
    parts={"signature-cactus": 1, "signature-code": 1, "stick-card": 1, "stick-rig": 1, "stick-words": 1},
)
