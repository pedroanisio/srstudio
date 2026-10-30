"""The release of representative."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "representative",
    InstagramPost(
        title="I only asked for a representative.",
        description=(
            "Two hours and forty-seven minutes on the line. Gus only wants a person. The menu is listening very "
            "carefully, and writing all of it down.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Liam (Gus), Alice (the menu) and Bill (the man); "
            "every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam, Alice and Bill. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=(
            "#customerservice",
            "#phonemenu",
            "#onhold",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("I said\nrepresentative.", 0.5, "Toon 24"),
    ),
    tags=Tags("money-services", "institution", "tension", test="sp-hook_motion", arm="a", recipient="a"),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-clipboard": 1,
        "toon-hallway": 1,
        "toon-hamster": 1,
        "toon-horse": 1,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-lounge": 1,
        "toon-phone": 1,
        "toon-speaker": 1,
    },
)
