"""The release of market-rate."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "market-rate",
    InstagramPost(
        title="Can we talk about my salary?",
        description=(
            "He got the job. Now he asks the boss for a raise, on the conference-room speakerphone. Record year! So, "
            "a raise? Better: a title. Then he finds his own job posted online, paying more. That's for external "
            "talent.\n"
            "Comedy Cut 16: the candidate from The Interview, a year in."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#salary",
            "#payraise",
            "#corporatelife",
            "#officehumor",
            "#workhumor",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Asking for\na raise.", 9.0, "Episode 16", (540, 900), 1.3, place="bottom"),
    ),
    cover=True,
    parts={
        "blinds-window": 1,
        "candidate": 1,
        "captions": 1,
        "conference-room": 1,
        "location-slate": 1,
        "notification": 1,
        "papers": 1,
        "password-card": 1,
        "scorecard": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "speakerphone": 1,
        "whiteboard": 1,
    },
)
