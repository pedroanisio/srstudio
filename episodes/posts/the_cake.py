"""The release of the-cake."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-cake",
    InstagramPost(
        title="Ten bucks for the cake?",
        description=(
            "Juno collects ten bucks from Pip for a cake. Not a birthday: someone is leaving. Bo arrives with it, "
            "delighted. The company saved a whole salary. The cake says WE'LL MISS YOU. Then Bo turns it round.\n"
            "Comedy Cut 19: Pip, Juno and Bo in the break room, pose to pose on a 120 bpm beat."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno), Will (Pip) and Eric (Bo). Music composed with "
        "ElevenLabs Music. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#officehumor",
            "#layoffs",
            "#corporatelife",
            "#workhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("We'll miss\nyou, Pip", 17.2, "Comedy Cut 19", place="top"),
    ),
)
