"""The release of wifi-password."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "wifi-password",
    InstagramPost(
        title="The Wi-Fi password is a sales tactic.",
        description=(
            "Comedy Cut 05, new cast: Ava the barista, Milo the customer and one park pigeon. The password is exactly "
            "what she said. No spaces. Five bucks well spent on a spelling lesson."
        ),
        credit="Voices: ElevenLabs premade voices Jessica and Liam. Procedural café and park sound effects.",
        hashtags=(
            "#TheInterview",
            "#cafehumor",
            "#wifipassword",
            "#baristalife",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
            "#pigeon",
        ),
        thumbnail=Thumbnail("What's the\nWi-Fi password?", 9.0, "Comedy Cut 05", (540, 560), 1.2),
    ),
    parts={
        "barista": 1,
        "bean-jar": 1,
        "bench": 1,
        "building": 1,
        "cafe": 1,
        "cafe-window": 1,
        "captions": 1,
        "coffee-cup": 1,
        "connected-card": 1,
        "customer": 1,
        "episode-slate": 1,
        "espresso-machine": 1,
        "location-slate": 1,
        "menu-board": 1,
        "park": 1,
        "park-sign": 1,
        "password-card": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "pigeon": 1,
        "shrub": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "tree": 1,
    },
)
