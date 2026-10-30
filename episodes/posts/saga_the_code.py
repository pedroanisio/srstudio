"""The release of saga-the-code."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-the-code",
    InstagramPost(
        title="The deadliest weapon in the galaxy needs a code sent to your phone",
        description=(
            "Lord Gloom orders the planet destroyed. The weapon wants to verify it's him: a code went to his phone. "
            "His phone is on that planet. So he calls it, and someone down there answers. Can they read him the "
            "code? It says never share this code with anyone.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Callum (Lord Gloom), Liam (Enforcer Seven) and Roger (Rook); the Directorate "
            "and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Callum, Liam and Roger. Sound effects generated with "
            "ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#twofactor",
            "#passwords",
            "#verificationcode",
            "#lostphone",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Fire the weapon?\nVerify it's you", 6.0, "Saga 13", (540, 890), 1.0),
    ),
    cover=True,
    tags=Tags(
        "everyday-tech",
        "institution",
        "embarrassment",
        recurring=("gloom", "seven", "rook"),
        test="sp-hook_motion",
        arm="a",
    ),  # fmt: skip
    parts={
        "saga-bridge": 1,
        "saga-enforcer": 1,
        "saga-entry": 1,
        "saga-gloom": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-rook": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
