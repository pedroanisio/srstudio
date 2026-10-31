"""The release of my-manager."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "my-manager",
    InstagramPost(
        title="Let me talk to my manager.",
        description=(
            "Who is he actually talking to?\n"
            "A Cutout sketch voiced with ElevenLabs premade voices George (the salesman) and Lily (Rosa); every "
            "character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices George and Lily. Sound effects generated with ElevenLabs.",
        hashtags=("#carshopping", "#carsales", "#adulting", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Twenty-three. Final.", 31.5, "Cutout"),
    ),
    cover=True,
    style="Cutout",
    tags=Tags("money-services", "other-person", "triumph", test="sp-hook_motion", arm="b"),
    comedy=Scores(author=18, reviewer=19),
    parts={
        # back-room, jump-clock, paper-poster and sandwich are drawn too; they stay out until they are approved: a
        # release cannot pin a proposed version.
        "captions": 1,
        "hiring-office": 1,
        "manager": 1,
        "papers": 1,
        "plant": 1,
        "roller-blind": 1,
        "rosa": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
