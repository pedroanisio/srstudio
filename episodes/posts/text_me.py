"""The release of text-me."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "text-me",
    InstagramPost(
        title="He lives four minutes away. She called the helicopter.",
        description=(
            "Four minutes. Six, tops. Then his phone died and there was a press conference.\n"
            "A Toon sketch, voiced with ElevenLabs premade voices Liam, Laura and Brian; original characters drawn in "
            "code."
        ),
        credit="Voices: ElevenLabs premade voices Liam (son), Laura (Mom) and Brian (neighbour). Foley synthesised.",
        hashtags=("#mom", "#momlife", "#familyhumor", "#animatedshorts", "#comedyshorts", "#cartoon"),
        thumbnail=Thumbnail("Text me when\nyou get home.", 8.2, "Toon 29", (500, 900), 1.1, place="top"),
    ),
    tags=Tags("family", "other-person", "affection", test="sp-hook_motion", arm="b", recipient="b", to="family"),
    style="toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-captions": 1,
        "toon-cat": 1,
        "toon-chopper": 1,
        "toon-clock": 1,
        "toon-desk": 1,
        "toon-fox": 2,
        "toon-home": 1,
        "toon-lower-third": 1,
        "toon-mics": 1,
        "toon-night-street": 1,
        "toon-paw": 1,
        "toon-phone": 1,
        "toon-press-room": 1,
        "toon-room": 1,
        "toon-sloth": 1,
        "toon-worktop": 1,
    },
)
