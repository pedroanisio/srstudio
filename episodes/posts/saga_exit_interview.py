"""The release of saga-exit-interview."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-exit-interview",
    InstagramPost(
        title="Why does nobody ever quit the Directorate?",
        description=(
            "Enforcer Seven has another offer. Is it the pay? The hours? The airlock? Lord Gloom threw Gary out of "
            "it: Gary was not a culture fit. What if they threw Seven a pizza party? What kind of pizza?\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Callum (Lord Gloom) and Liam (Seven); the Directorate and every character "
            "are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Callum and Liam. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=(
            "#exitinterview",
            "#culturefit",
            "#quitting",
            "#officelife",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Why does nobody\never quit?", 8.0, "Saga 09", (540, 890), 1.0),
    ),
    cover=True,
    # its cover drawing changed after it was published; the operator froze it as published (ADR 0040)
    frozen="8b00377830d82ee599e0d92feebddd34522e102d1e10b20f3369a0dc505e2622",
    parts={
        "saga-bridge": 1,
        "saga-enforcer": 1,
        "saga-entry": 1,
        "saga-gloom": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
