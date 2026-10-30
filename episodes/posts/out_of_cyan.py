"""The release of out-of-cyan."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "out-of-cyan",
    InstagramPost(
        title="One black page. The printer wants cyan.",
        description=(
            "There is no cyan in black. The printer knows this. It has your document, it has terms, and it has a "
            "photo.\nRosa, from the elevator, at home and losing."
        ),
        credit="Voice: ElevenLabs premade voice Lily. Sound effects generated with ElevenLabs.",
        hashtags=("#printer", "#homeoffice", "#everydaylife", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("It wants cyan.\nFor a black page.", 0.5, "Printing one page"),
    ),
    cover=True,
    tags=Tags(
        "everyday-tech", "institution", "tension", recurring=("rosa",), test="sp-hook_motion", arm="a", recipient="a"
    ),  # fmt: skip
    style="Cutout",
    parts={"captions": 1, "card-reader": 1, "papers": 1, "rosa": 1, "signature-cactus": 1, "signature-code": 1},
    parts={
        "captions": 1,
        "card-reader": 1,
        "desk-printer": 1,
        "home-study": 1,
        "hostage-photo": 1,
        "paper-bag": 1,
        "papers": 1,
        "ransom-note": 1,
        "rosa": 1,
        "shop-till": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
