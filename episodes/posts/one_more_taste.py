"""The release of one-more-taste."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "one-more-taste",
    InstagramPost(
        title="Can I try the pistachio?",
        description=(
            "There is one in every line. Sometimes it is you."
            "\n"
            "A Toon sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Alice, Liam, Bill and George. Foley synthesised.",
        hashtags=('#icecream', '#waitinginline', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Can I try\nthe pistachio?", 1.0, "Toon 35"),
    ),
    tags=Tags(
        "money-services",
        "other-person",
        "recognition",
        recurring=("bruno",),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-cone": 1,
        "toon-fox": 2,
        "toon-goat": 1,
        "toon-hamster": 1,
        "toon-key-line": 1,
        "toon-parlour-back": 1,
        "toon-parlour-case": 1,
        "toon-parlour-front": 1,
    },
    comedy=Scores(18, 18),
)
