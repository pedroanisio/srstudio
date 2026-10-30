"""The release of take-one."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "take-one",
    InstagramPost(
        title="Forty-seven takes of one word. We'll use the first one.",
        description=(
            "Omar reads the news for a living. Today he is in the booth to say one word for a kids' show, and Jun "
            "has notes: happier, sadder, sad but he just found a hat.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Will (Jun) and Daniel (Omar), lip-synced to their "
            "words; BOWLHEADS is an invented show, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Daniel. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#voiceover", "#voiceacting", "#director", "#notes", "#filmmaking", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Just the\none word.", 0.5, "Collage 18", (600, 1000), 1.3, place="bottom"),
    ),
    tags=Tags("office", "other-person", "embarrassment", recurring=("jun", "omar"), test="sp-hook_motion", arm="a"),
    parts={
        "collage-jun": 1,
        "collage-omar": 1,
        "collage-sign": 1,
        "collage-stage": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
