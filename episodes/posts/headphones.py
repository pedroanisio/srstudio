"""The release of headphones."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "headphones",
    InstagramPost(
        title="How loud are you with headphones in?",
        description=(
            "Aisle four knows about Harold."
            "\n"
            "A Cutout sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Lily (Rosa), Liam (Milo) and Daniel (the loudspeaker). Foley "
        "synthesized.",
        hashtags=("#headphones", "#supermarket", "#relatable", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("How loud are you\nwith headphones in?", 3.0, "Okayville"),
    ),
    cover=True,
    tags=Tags(
        "own-worst-enemy",
        "protagonist",
        "embarrassment",
        recurring=("rosa", "milo"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Cutout",
    parts={
        "barista": 1,
        "candidate": 1,
        "captions": 1,
        "coffee-cup": 1,
        "customer": 1,
        "hand-basket": 1,
        "manager": 1,
        "rosa": 1,
        "shelf-goods": 1,
        "shopping-cart": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "store-aisle": 1,
    },
    comedy=Scores(18, 19),
)
