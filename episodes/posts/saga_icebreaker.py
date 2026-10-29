"""The release of saga-icebreaker."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-icebreaker",
    InstagramPost(
        title="Is there anything worse than a team icebreaker?",
        description=(
            "One fun fact about yourself. Seven has never hit a target. The droid is technically a toaster. Lord "
            "Gloom can hear your thoughts. Great icebreaker, my lord. Now say it in your head.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Liam (Seven), Callum (Lord Gloom) and Jessica (the droid); the Directorate "
            "and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Liam, Callum and Jessica. Sound effects generated with "
            "ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#icebreaker",
            "#teambuilding",
            "#officelife",
            "#workcomedy",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Worse than an\nicebreaker?", 12.0, "Saga 08", (540, 890), 1.0),
    ),
    cover=True,
)
