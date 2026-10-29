"""The release of the-viewing."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-viewing",
    InstagramPost(
        title="Is that a toilet in the kitchen?",
        description=(
            "Flat hunting, day 41. The kitchen is open plan: cook and multitask. The window is hand-painted, so the "
            "view never changes. The bed folds down, and it comes with Gary. Two grand a month, each. Dev takes it. "
            "He is applicant forty-seven.\n"
            "A stick-figure cartoon voiced with ElevenLabs premade voices Will, Lily and Callum; original characters "
            "drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will, Lily and Callum. Sound effect generated with ElevenLabs; "
        "music composed with ElevenLabs Music.",
        hashtags=(
            "#flathunting",
            "#rent",
            "#landlord",
            "#adulting",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("He comes\nwith the lease.", 14.0, "Stick 05", (540, 1000), 1.0),
    ),
    cover=True,
)
