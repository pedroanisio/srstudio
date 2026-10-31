"""The release of low-balance."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "low-balance",
    InstagramPost(
        title="A $12 fee for having too little.",
        description=(
            "Is anything in this bank free?\n"
            "A Cutout sketch voiced with ElevenLabs premade voices Liam (the customer) and George (the teller); every "
            "character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Liam and George. Sound effects generated with ElevenLabs.",
        hashtags=("#bankfees", "#banking", "#adulting", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("The pen is free.", 28.55, "Cutout"),
    ),
    cover=True,
    style="Cutout",
    tags=Tags("money-services", "institution", "recognition", test="sp-hook_motion", arm="b"),
    comedy=Scores(author=17, reviewer=18),
    parts={
        "candidate": 1,
        "captions": 1,
        "card-reader": 1,
        "globe-pendant": 1,
        "manager": 1,
        "paper-poster": 1,
        "pen-on-chain": 1,
        "reception": 1,
        "reception-counter": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "slat-wall": 1,
    },
)
