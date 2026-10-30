"""The release of missed-you."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "missed-you",
    InstagramPost(
        title="Delivery: today, 8am–8pm.",
        description=(
            "She brought a chair. He brought a note. Nobody brought the parcel.\n"
            "A Toon sketch, voiced with ElevenLabs premade voice Charlie; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voice Charlie (Rex). Foley synthesised.",
        hashtags=("#delivery", "#deliveryproblems", "#waiting", "#animatedshorts", "#comedyshorts", "#cartoon"),
        thumbnail=Thumbnail("Sorry we missed you.", 16.0, "Toon 31"),
    ),
    tags=Tags("money-services", "institution", "triumph", test="sp-hook_motion", arm="b", recipient="a"),
    style="toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-captions": 1,
        "toon-clock": 1,
        "toon-dog": 2,
        "toon-frog": 2,
    },
)
