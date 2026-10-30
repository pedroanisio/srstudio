"""The release of camera-off."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "camera-off",
    InstagramPost(
        title="Camera off. Pajamas on the beat.",
        description=(
            "Pip is very professional on the call. Then the boss announces forty slides, the camera goes off and "
            "the dancing starts, until someone asks him to share his screen.\n"
            "Episode 08, the second in the Soft style: every pose lands on the beat."
        ),
        credit=(
            "Song composed and sung with the ElevenLabs Music API. Boss: ElevenLabs premade voice Eric. "
            "Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#cameraoff",
            "#zoommeeting",
            "#workfromhome",
            "#remotework",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Camera off.\nPajamas on.", 10.0, "Episode 08", (560, 1000), 1.25),
    ),
    parts={
        "captions": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-chair": 1,
        "soft-desk": 1,
        "soft-laptop": 1,
        "soft-office": 1,
    },
)
