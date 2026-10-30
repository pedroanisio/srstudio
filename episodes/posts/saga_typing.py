"""The release of saga-typing."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-typing",
    InstagramPost(
        title="She is sitting right next to me. She texted: we need to talk.",
        description=(
            "Rook gets a text from Juno: we need to talk. Juno is in the next seat. Then she is typing. Then she "
            "stops. Then she types a lot. Is it the ship? Is it his cousin? It is about the snacks. Two can play at "
            "this.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator) and Roger (Rook); the Directorate and every character are original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George and Roger. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#typing",
            "#weneedtotalk",
            "#texting",
            "#relationships",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("We need to talk.\nJuno is typing...", 8.6, "Saga 17", (540, 890), 1.0),
    ),
    cover=True,
    tags=Tags(
        "everyday-tech", "other-person", "tension", recurring=("rook", "juno"), test="sp-hook_motion", arm="a"
    ),  # fmt: skip
    parts={
        "saga-cockpit": 1,
        "saga-cockpit-console": 1,
        "saga-entry": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-juno": 1,
        "saga-rook": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
