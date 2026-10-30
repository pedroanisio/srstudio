"""The release of friday-sync."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "friday-sync",
    InstagramPost(
        title="Why is there a meeting on Friday evening?",
        description=(
            "Bruno booked a quick sync for Friday evening. It's nothing bad: Pip just needs to train the new hire. "
            "Then a job alert: her own job, for less money. Can she apply for it? Sorry. She's overqualified.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Alice (Pip) and Bill (Bruno), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice and Bill. Original characters, drawn in code.",
        hashtags=(
            "#fridayfeeling",
            "#jobsearch",
            "#replaced",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("A meeting on\nFriday evening?", 1.0, "Toon 15", (470, 1130), 1.35),
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
        "toon-toast": 1,
    },
)
