"""The release of hold-the-door."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "hold-the-door",
    InstagramPost(
        title="You held the door too early.",
        description=(
            "They were too far away. You knew it. They knew it. And now they have to do the little run.\n"
            "Stick 10: one door, one arm, a long street, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will, Liam, Sarah, Chris and Lily. Sound effects with ElevenLabs.",
        hashtags=("#awkward", "#everydayhumor", "#socialanxiety", "#manners", "#stickfigure", "#animatedshorts"),
        thumbnail=Thumbnail("You held\nthe door\ntoo early.", 0.5, "Stick 10", (540, 860), 1.0, place="top"),
    ),
    cover=True,
    tags=Tags(
        "relationships",
        "protagonist",
        "embarrassment",
        recurring=("dev",),
        test="sp-hook_motion",
        arm="a",
        recipient="a",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-entrance": 1,
        "stick-glass-door": 1,
        "stick-marathon": 1,
        "stick-rig": 1,
        "stick-snow-cap": 1,
        "stick-street-lens": 1,
        "stick-words": 1,
    },
)
