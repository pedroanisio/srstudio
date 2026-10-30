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
    characters={"barista": 1, "customer": 1, "pigeon": 1},
)
