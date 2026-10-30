"""The release of unlimited-pto."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "unlimited-pto",
    InstagramPost(
        title="Who wants unlimited vacation?",
        description=(
            "Bo has big news: unlimited time off. Pip asks for Friday. Then Friday afternoon. Then lunch. Declined, "
            "declined, declined. So how many days is unlimited? Unlimited: that's why nobody needs one.\n"
            "Comedy Cut 13, Bo's first time on screen: a one-on-one in the meeting room, every pose on the beat."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Eric (Bo) and Will (Pip). Music composed with ElevenLabs Music. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#unlimitedpto",
            "#vacation",
            "#officehumor",
            "#workcomedy",
            "#corporatelife",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Unlimited\nvacation?", 4.6, "Episode 13", place="top"),
    ),
    cover=True,
    characters={"bo": 1, "pip": 1},
)
