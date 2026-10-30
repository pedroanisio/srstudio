"""The release of quick-question."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "quick-question",
    InstagramPost(
        title="Quick question. Got a sec?",
        description=(
            "Pip has a quick question. First, some context. It started in March. Then Dave left. Forty-six "
            "minutes later: when's the stand-up? Three minutes ago. It's on the board behind her.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#quickquestion",
            "#officehumor",
            "#workcomedy",
            "#standupmeeting",
            "#animatedshorts",
            "#vectoranimation",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Quick question.\nGot a sec?", 1.0, "Toon 05", (340, 1050), 1.3),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-bear": 1,
        "toon-board-text": 1,
        "toon-captions": 1,
        "toon-clock": 1,
        "toon-desk": 1,
        "toon-meeting": 1,
        "toon-mug": 1,
        "toon-notes": 1,
        "toon-rabbit": 1,
        "toon-room": 1,
    },
)
