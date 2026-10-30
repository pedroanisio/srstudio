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
    # its cover drawing changed after it was published; the operator froze it as published (ADR 0040)
    frozen="59d9c36a3aec7bbc260cb6549585360c209f5f0c192117d3ebac808ad853cacb",
    parts={
        "saga-bridge": 1,
        "saga-droid": 1,
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
