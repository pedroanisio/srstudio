"""The release of cup-fee."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "cup-fee",
    InstagramPost(
        title="Three bucks for a black coffee. Plus a fee for the cup.",
        description=(
            "Then the lid fee. Then a service fee, for serving you. Pay in cash and there is a fee for that too. So "
            "Milo asks what the coffee itself costs.\n"
            "Comedy Cut 22: Ava and Milo from Tip Screen, back at the café counter."
        ),
        credit="Voices: ElevenLabs premade voices Jessica and Liam. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#hiddenfees",
            "#coffeeshop",
            "#junkfees",
            "#adulting",
            "#everydaylife",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail(
            "Three bucks.\nPlus fees.", 14.3, "Comedy Cut 22"
        ),  # the reader at $7.75, before the reveal
    ),
    cover=True,
    tags=Tags(
        "money-services", "institution", "recognition", recurring=("ava", "milo"), test="sp-hook_motion", arm="a"
    ),
    characters={"barista": 1, "customer": 1},
)
