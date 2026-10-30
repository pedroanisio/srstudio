"""The release of best-angle."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "best-angle",
    InstagramPost(
        title="Video calling your mom: forehead, half a face, then the wall.",
        description=(
            "Rosa video-calls her son and finds every angle except her face. Gary talks her through it from work. "
            "When she finally gets it right, she has one question for him.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa) and Chris (Gary), lip-synced to "
            "their words; BOWLHEADS is an invented show, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda and Chris. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#videocall", "#mom", "#facetime", "#techsupport", "#brainrot", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Mom, I can only\nsee your forehead.", 1.5, "Collage 15", None, 1.0, place="top"),
    ),
    tags=Tags(
        "everyday-tech", "other-person", "embarrassment", recurring=("rosa", "gary"), test="sp-hook_motion", arm="b"
    ),
    parts={
        "collage-boardroom": 1,
        "collage-call-buttons": 1,
        "collage-flush": 1,
        "collage-gary": 1,
        "collage-living-room": 1,
        "collage-rosa": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
