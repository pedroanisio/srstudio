"""The release of who-touched-it."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "who-touched-it",
    InstagramPost(
        title="He was asleep. He was upstairs.",
        description=(
            "One degree. That is all it was. Nobody has ever got away with one degree.\n"
            "A Toon sketch voiced with ElevenLabs premade voices River (the kid) and Brian (Dad); every character "
            "is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices River and Brian. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#thermostat",
            "#dadsbelike",
            "#familyhumor",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Dad is asleep\nupstairs.", 0.5, "Toon 25"),
    ),
    tags=Tags("family", "other-person", "affection", test="sp-hook_motion", arm="a", recipient="b", to="family"),
    style="Toon",
    parts={"signature-cactus": 1, "signature-code": 1, "toon-captions": 1, "toon-goat": 1, "toon-hedgehog": 2},
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bedroom": 1,
        "toon-captions": 1,
        "toon-finger": 1,
        "toon-goat": 1,
        "toon-hallway": 1,
        "toon-hedgehog": 2,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-quilt": 1,
        "toon-thermostat": 1,
        "toon-vent": 1,
    },
)
