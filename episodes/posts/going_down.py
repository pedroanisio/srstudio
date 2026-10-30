"""The release of going-down."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "going-down",
    InstagramPost(
        title="Am I being fired?",
        description=(
            "No. Your role is being sunset. You're going fully remote: from your couch, forever. Floor 4, the doors "
            "open, and Kevin, the pigeon who is now Head of People, flies in for this, with a pink slip in his beak. "
            "He drops it. It's not for you.\n"
            "Comedy Cut 20, the office finale: the boss, the employee from Market Rate and Elevator Pitch, and the "
            "pigeon from Culture Fit, back on the bench where it all began."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#layoffs",
            "#corporatespeak",
            "#officehumor",
            "#remotework",
            "#animatedshorts",
            "#cartoon",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Am I being\nfired?", 1.0, "Comedy Cut 20", place="top"),
    ),
    cover=True,
    parts={
        "bench": 1,
        "building": 1,
        "candidate": 1,
        "captions": 1,
        "crumbs": 1,
        "elevator": 1,
        "location-slate": 1,
        "manager": 1,
        "park": 1,
        "park-sign": 1,
        "pigeon": 1,
        "pink-slip": 1,
        "scorecard": 1,
        "shrub": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "tree": 1,
    },
)
