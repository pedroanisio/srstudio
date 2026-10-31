"""The release of network-names."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "network-names",
    InstagramPost(
        title="He doesn't know it's us.",
        description=(
            "Who's Turn It Down?\n"
            "A Toon sketch voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno); every character is "
            "original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah and Bill. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#wifi", "#neighbors", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Turn It Down", 7.0, "Toon"),
    ),
    tags=Tags("everyday-tech", "other-person", "affection", test="sp-hook_motion", arm="b"),
    style="Toon",
    comedy=Scores(author=18, reviewer=18),
    parts={
        # toon-wifi-list is drawn too and still proposed: a release cannot pin a proposed
        # version.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-lounge": 1,
        "toon-phone": 1,
        "toon-rabbit": 2,
        "toon-sofa": 1,
        "toon-speaker": 1,
    },
)
