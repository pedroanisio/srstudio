"""The release of elevator-pitch."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "elevator-pitch",
    InstagramPost(
        title="Working from home? Elevator pitch. You've got till my floor.",
        description=(
            "He pitches it: more productive, no commute, no meetings. Floor 4, the doors open, and in walks Kevin, "
            "the pigeon the boss hired on his lunch break. Kevin is fully remote. He flies in on Tuesdays. He "
            "negotiated; you took a title. Floor 9: Kevin, your call.\n"
            "Comedy Cut 18: the boss, the employee from Market Rate and the pigeon from Culture Fit, in a new elevator."
        ),
        credit="Voices: ElevenLabs premade voices Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#workfromhome",
            "#returntooffice",
            "#elevatorpitch",
            "#officehumor",
            "#animatedshorts",
            "#cartoon",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Elevator\npitch", 8.6, "Comedy Cut 18", place="top"),
    ),
    cover=True,
)
