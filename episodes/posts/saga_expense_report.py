"""The release of saga-expense-report."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-expense-report",
    InstagramPost(
        title="Who approves a dark lord's expenses?",
        description=(
            "One planet, destroyed; the receipt exploded. The cape is personal. The helmet is personal. The "
            "breathing machine is personal. The planet is approved: just attach a photo of it. Then it's personal.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Callum (Lord Gloom) and Jessica (the droid); the Directorate and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Callum and Jessica. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#expenses",
            "#expensereport",
            "#finance",
            "#officelife",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Who approves\nhis expenses?", 10.0, "Saga 11", (540, 890), 1.0),
    ),
    cover=True,
)
