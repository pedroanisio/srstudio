"""The release of reply-all."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "reply-all",
    InstagramPost(
        title="Bruno. Did you just reply all?",
        description=(
            "Bruno meant to send it to Pip. He sent it to the whole company: this meeting could have been an email. "
            "The CEO agrees, and cancels every meeting. He's a hero. Then the CEO again: your job, also an email.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=("#replyall", "#email", "#meetings", "#officehumor", "#workcomedy", "#animatedshorts", "#lipsync"),
        thumbnail=Thumbnail("Did you just\nreply all?", 0.8, "Toon 17", (470, 1130), 1.35),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-bear": 1,
        "toon-captions": 1,
        "toon-clock": 1,
        "toon-desk": 1,
        "toon-home": 1,
        "toon-mug": 1,
        "toon-notes": 1,
        "toon-rabbit": 1,
        "toon-room": 1,
        "toon-toast": 1,
    },
)
