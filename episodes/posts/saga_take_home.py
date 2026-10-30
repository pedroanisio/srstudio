"""The release of saga-take-home."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-take-home",
    InstagramPost(
        title="Interview round six: design a battle station, unpaid, due Monday",
        description=(
            "Juno reaches round six of a Directorate job interview. It's just a little homework: design a battle "
            "station. She sends four hundred pages. They went with another candidate. Then a battle station fills "
            "the sky, and they're hiring for it: ten years of experience required.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Callum (Lord Gloom) and River (Juno); the Directorate and every character "
            "are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Callum and River. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#jobsearch",
            "#jobinterview",
            "#takehometest",
            "#jobhunting",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Interview round six:\nunpaid homework", 8.0, "Saga 14", (540, 890), 1.0),
    ),
    cover=True,
    tags=Tags(
        "job-hunting", "institution", "recognition", recurring=("gloom", "juno"), test="sp-hook_motion", arm="b"
    ),  # fmt: skip
)
