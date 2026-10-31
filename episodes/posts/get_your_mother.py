"""The release of get-your-mother."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "get-your-mother",
    InstagramPost(
        title="When did you last call your dad on purpose?",
        description=(
            "He got to the phone first. He has a procedure for that. Fern had other plans.\n"
            "A Toon sketch on Okayville, voiced with ElevenLabs premade voices Brian (Dad), Matilda (Fern), Laura "
            "(Mom) and Roger (the neighbor); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian, Matilda, Laura and Roger. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=("#dadsbelike", "#phonecalls", "#family", "#animatedshorts", "#okayville"),
        thumbnail=Thumbnail("She called\nme.", 27.5, "Okayville"),
    ),
    tags=Tags("family", "other-person", "affection", recurring=("fern",), test="sp-hook_motion", arm="b"),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-frog": 2,
        "toon-goat": 1,
        "toon-home": 1,
        "toon-key-line": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-phone": 1,
        "toon-sloth": 1,
        "toon-yard": 1,
    },
    comedy=Scores(author=16, reviewer=18),
)
