"""The release of im-quitting."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "im-quitting",
    InstagramPost(
        title="He is quitting today. He has been quitting today for forty years.",
        description=(
            "The coffee machine has heard every resignation. So has the man beside it, who has one reply.\n"
            "Every office has him. Most offices have him at the coffee machine."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=("#officelife", "#coworkers", "#workhumor", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("I'm quitting.\nToday.", 3.6, "Day 2,190"),
    ),
    cover=True,
    tags=Tags(
        "office", "other-person", "recognition", test="sp-hook_motion", arm="b", recipient="b", to="work friend"
    ),  # fmt: skip
    style="Cutout",
    parts={"candidate": 1, "captions": 1, "manager": 1, "plant": 1, "signature-cactus": 1, "signature-code": 1},
    parts={
        "break-room": 1,
        "candidate": 1,
        "captions": 1,
        "days-board": 1,
        "drip-machine": 1,
        "gold-watch": 1,
        "manager": 1,
        "office-mug": 1,
        "office-party": 1,
        "party-crowd": 1,
        "plant": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "stage-mic": 1,
        "wall-planner": 1,
    },
)
