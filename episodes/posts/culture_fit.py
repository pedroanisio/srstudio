"""The release of culture-fit."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "culture-fit",
    InstagramPost(
        title="Where do you see yourself in five years?",
        description=(
            "Job hunt, day 200: two hundred applications, not one reply. Then the boss sits down on the same bench "
            "for lunch, and a pigeon lands at his feet. The pigeon interviews well.\n"
            "Comedy Cut 14: Milo from The Wi-Fi Password meets the boss from The Interview, in the park."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#jobhunting",
            "#jobsearch",
            "#hiring",
            "#adulting",
            "#officehumor",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("He works\nfor crumbs.", 17.75, "Episode 14", (560, 820), 1.1, place="bottom"),
    ),
    cover=True,
    parts={
        "bench": 1,
        "building": 1,
        "captions": 1,
        "coffee-cup": 1,
        "crumbs": 1,
        "customer": 1,
        "location-slate": 1,
        "manager": 1,
        "notification": 1,
        "park": 1,
        "park-sign": 1,
        "pigeon": 1,
        "scorecard": 1,
        "shrub": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "tree": 1,
    },
)
