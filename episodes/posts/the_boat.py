"""The release of the-boat."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-boat",
    InstagramPost(
        title="What dentist?",
        description=(
            "Ever had your earbuds die in public?\n"
            "A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb), Daniel (Omar), Sarah (Priya), Will "
            "(Jun), Brian (Brent) and Laura (the phone), lip-synced to their words; every character is original, "
            "drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, Daniel, Sarah, Will, Brian and Laura. Original characters, "
            "drawn in code. Sound effects synthesised in code."
        ),
        hashtags=("#earbuds", "#publictransit", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("What dentist?", 18.9, "Collage"),
    ),
    tags=Tags(
        "everyday-tech",
        "protagonist",
        "embarrassment",
        recurring=("deb", "omar", "priya", "jun", "brent"),
        test="sp-hook_motion",
        arm="a",
    ),
    style="Collage",
    comedy=Scores(author=18, reviewer=18),
    parts={
        "collage-brent": 1,
        "collage-bus-stop": 1,
        "collage-deb": 1,
        "collage-jun": 1,
        "collage-omar": 1,
        "collage-phone": 1,
        "collage-priya": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        # collage-battery-insert stays out until it is approved: a release cannot pin a proposed version.
    },
)
