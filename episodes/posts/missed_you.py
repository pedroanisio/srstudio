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
        "toon-far-wall": 1,
        "toon-frog": 2,
        "toon-front-door": 1,
        "toon-hall-chair": 1,
        "toon-missed-slip": 1,
        "toon-paw": 1,
        "toon-porch": 1,
        "toon-stuck-note": 1,
        "toon-van": 1,
        "toon-worktop": 1,
        "toon-yard": 1,
    },
)
