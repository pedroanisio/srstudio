"""The release of loaded-right."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "loaded-right",
    InstagramPost(
        title="Who taught you to load a dishwasher?",
        description=(
            "Dad has a file on every boyfriend. It has never once mattered "
            "what was in it.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Brian (Dad), "
            "Matilda (Fern) and Will (Lewis); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian, Matilda and Will. Original characters, drawn in code. Sound"
            " effects synthesized in code."
        ),
        hashtags=('#dishwasher', '#dadsbelike', '#meettheparents', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Mugs on\na slant.", 17.5, "Okayville"),
    ),
    tags=Tags("family", "other-person", "affection", recurring=('fern',), test="sp-hook_motion", arm="b"),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dishwasher": 1,
        "toon-frog": 2,
        "toon-goat": 1,
        "toon-hamster": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-paw": 1,
        "toon-raccoon": 2,
        "toon-rack": 1,
    },
    comedy=Scores(author=16, reviewer=18),
)
