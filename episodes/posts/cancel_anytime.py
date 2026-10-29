"""The release of cancel-anytime."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "cancel-anytime",
    InstagramPost(
        title="How do I cancel my gym membership?",
        description=(
            "Cancel anytime, says the sign. In person: he's here. On a Tuesday: it's Tuesday. Before sunrise: it's "
            "still dark. With a note from the trainer he has never met. Any other way? A death certificate. Whose? "
            "They're flexible.\n"
            "A stick-figure cartoon voiced with ElevenLabs premade voices Callum and Jessica."
        ),
        credit="Voices: ElevenLabs premade voices Callum and Jessica. Instrumental music composed with ElevenLabs "
        "Music.",
        hashtags=(
            "#gymmembership",
            "#cancelanytime",
            "#fineprint",
            "#subscriptions",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Cancel\nanytime*", 1.0, "Stick 06", (540, 1200), 1.3),
    ),
    cover=True,
)
