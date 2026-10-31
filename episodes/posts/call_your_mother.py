"""The release of call-your-mother."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "call-your-mother",
    InstagramPost(
        title="Would you let your mom negotiate your salary?",
        description=(
            "He was really flexible. She has never been flexible in"
            " her life.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Jessica (Dana), Liam "
            "(the son) and Laura (Mom); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, Liam and Laura. Original characters, drawn in code. Sound"
            " effects synthesized in code."
        ),
        hashtags=('#salary', '#jobinterview', '#momsbelike', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("He is not\nflexible.", 16.5, "Okayville"),
    ),
    tags=Tags("job-hunting", "other-person", "triumph", recurring=('dana',), test="sp-hook_motion", arm="b"),
    style="Toon",
    parts={
        # toon-plate-of-toast also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bedroom": 1,
        "toon-captions": 1,
        "toon-cat": 1,
        "toon-desk": 1,
        "toon-dog": 2,
        "toon-fox": 2,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-meeting": 1,
        "toon-phone": 1,
    },
    comedy=Scores(author=15, reviewer=19),
)
