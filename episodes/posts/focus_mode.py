"""The release of focus-mode."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "focus-mode",
    InstagramPost(
        title="Focus. The deadline is... oh.",
        description=(
            "Pip sits down to work, types for one bar, and the groove wins. A record scratch: the deadline. Focus. "
            "Then he checks the date.\n"
            "Episode 07, the first in the Soft style: every pose lands on the beat."
        ),
        credit="Voice: ElevenLabs premade voice Will. Music composed with ElevenLabs Music.",
        hashtags=(
            "#focusmode",
            "#deadline",
            "#procrastination",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Shake it\nto the beat!", 10.0, "Episode 07", (620, 1000), 1.3),
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
