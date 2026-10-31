"""The release of long-goodbye."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "long-goodbye",
    InstagramPost(
        title="How long does it take to leave your mom's house?",
        description=(
            "He said goodbye at 7:02. She heard it as an opening"
            " statement.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Liam (the son) and "
            "Laura (Mom); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam and Laura. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#momsbelike', '#leftovers', '#family', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("This is\nthe highway.", 15.4, "Okayville"),
    ),
    tags=Tags("family", "other-person", "recognition", test="sp-hook_motion", arm="b"),
    style="Toon",
    parts={
        # toon-car-inside, toon-soup-tubs also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-cat": 1,
        "toon-fox": 2,
        "toon-hallway": 1,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-lounge": 1,
        "toon-porch": 1,
        "toon-road": 1,
        "toon-speaker": 1,
        "toon-worktop": 1,
        "toon-yard": 1,
    },
    comedy=Scores(author=15, reviewer=18),
)
