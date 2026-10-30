"""The release of tip-screen."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "tip-screen",
    InstagramPost(
        title="How would you like to tip me for ordering?",
        description=(
            "A black coffee, poured from a pot, with intention. Then the tablet swivels: 20%, 25%, 30%. So Milo "
            "brought a tablet of his own.\n"
            "Comedy Cut 12: Ava and Milo from The Wi-Fi Password, back in the café, tapping until closing time."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Jessica. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#tipping",
            "#tipscreen",
            "#coffeeshop",
            "#adulting",
            "#officehumor",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Tip me for\nordering?", 12.0, "Episode 12", place="top"),
    ),
    cover=True,
    parts={
        "barista": 1,
        "bean-jar": 1,
        "cafe": 1,
        "cafe-window": 1,
        "captions": 1,
        "coffee-cup": 1,
        "customer": 1,
        "episode-slate": 1,
        "espresso-machine": 1,
        "location-slate": 1,
        "menu-board": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "scorecard": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "tip-tablet": 1,
    },
)
