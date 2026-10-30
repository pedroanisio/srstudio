"""The release of saga-friday-deploy."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-friday-deploy",
    InstagramPost(
        title="One tiny fix at five on a Friday. What could go wrong?",
        description=(
            "Seven ships one tiny fix before the weekend. Lord Gloom points out it is Friday. The bridge goes dark. "
            "It works on Seven's machine, and his machine is the ship. Only he can roll it back, and he is on leave "
            "until Monday.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Liam (Enforcer Seven) and Callum (Lord Gloom); the Directorate and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Liam and Callum. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#fridaydeploy",
            "#devops",
            "#softwareengineering",
            "#itworksonmymachine",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("One tiny fix\nat five on a Friday", 8.0, "Saga 18", (540, 890), 1.0),
    ),
    cover=True,
    tags=Tags(
        "office", "protagonist", "recognition", recurring=("seven", "gloom"), test="sp-hook_motion", arm="b"
    ),  # fmt: skip
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
