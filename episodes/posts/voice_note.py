"""The release of voice-note."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "voice-note",
    InstagramPost(
        title="Quick one.",
        description=(
            "What's the big news?\n"
            "A Toon sketch voiced with the ElevenLabs premade voice Jessica (the friend); every character is "
            "original, drawn in code."
        ),
        credit=(
            "Voice: ElevenLabs premade voice Jessica. Original characters, drawn in code. Sound effects synthesized "
            "in code."
        ),
        hashtags=("#voicenote", "#friends", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Quick one.", 3.0, "Toon"),
    ),
    tags=Tags("everyday-tech", "other-person", "recognition", test="sp-hook_motion", arm="a"),
    style="Toon",
    comedy=Scores(author=18, reviewer=17),
    parts={
        # toon-voice-note-bar is drawn too and still proposed: a release cannot pin a proposed
        # version.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bedroom": 1,
        "toon-captions": 1,
        "toon-hedgehog": 2,
        "toon-home": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-phone": 1,
        "toon-plant": 1,
        "toon-quilt": 1,
        "toon-sink": 1,
        "toon-suds": 1,
        "toon-tee": 1,
        "toon-watering-can": 1,
    },
)
