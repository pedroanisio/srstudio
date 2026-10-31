"""The release of scan-the-code."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "scan-the-code",
    InstagramPost(
        title="Could I see a menu?",
        description=(
            "Why does the pigeon get paper?\n"
            "A Cutout sketch voiced with ElevenLabs premade voices Liam (Milo), Jessica (Ava) and Alice (the phone); "
            "every character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Liam, Jessica and Alice. Sound effects generated with ElevenLabs.",
        hashtags=("#qrcode", "#coffeeshop", "#adulting", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Scan me.", 16.5, "Cutout"),
    ),
    cover=True,
    style="Cutout",
    tags=Tags("money-services", "institution", "relief", test="sp-hook_motion", arm="b"),
    comedy=Scores(author=17, reviewer=15),
    parts={
        "barista": 1,
        "bean-jar": 1,
        "cafe": 1,
        "cafe-table": 1,
        "cafe-window": 1,
        "captions": 1,
        "coffee-cup": 1,
        "customer": 1,
        "espresso-machine": 1,
        "menu-board": 1,
        "paper-menu": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "phone-screen": 1,
        "pigeon": 1,
        "qr-code": 1,
        "reaching-hand": 1,
        "rising-bubbles": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soup-bowl": 1,
        "table-tent": 1,
        "water-glass": 1,
        "water-splash": 1,
    },
)
