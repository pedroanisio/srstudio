"""The release of return-to-office."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "return-to-office",
    InstagramPost(
        title="Two hours on a train. For this?",
        description=(
            "Day one of the return to office. Pip commutes two hours to an empty meeting room, and the boss "
            "welcomes the team back on the wall screen. From a beach. Leadership is hybrid.\n"
            "Comedy Cut 15: Pip and Bo, pose to pose on a 120 bpm beat."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Music composed with ElevenLabs Music. Sound effects "
        "generated with ElevenLabs.",
        hashtags=(
            "#returntooffice",
            "#rto",
            "#hybridwork",
            "#officehumor",
            "#corporatelife",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Someone has to\nbe the culture.", 19.2, "Episode 15", place="bottom"),
    ),
    cover=True,
)
