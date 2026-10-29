"""The release of group-nine."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "group-nine",
    InstagramPost(
        title="Is Group 9 boarding yet?",
        description=(
            "Group 9 boards after the luggage. Your bag is Group 4, and it's doing great. Group 8 costs extra: same "
            "seat, you just board feeling chosen. The plane can't leave without you? Everyone says that.\n"
            "Stick 08: a boarding gate, a podium, a carry-on and a cabin row drawn in code, the captions one word at "
            "a time."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Matilda. Sound effect and instrumental music composed with "
        "ElevenLabs.",
        hashtags=(
            "#travelhumor",
            "#airlines",
            "#boardinggroup",
            "#officehumor",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Is Group 9\nboarding yet?", 1.0, "Stick 08", place="top"),
    ),
    cover=True,
)
