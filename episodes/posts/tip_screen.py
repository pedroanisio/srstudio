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
    characters={"barista": 1, "customer": 1},
)
