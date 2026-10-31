"""The release of your-lasagna."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "your-lasagna",
    InstagramPost(
        title="Bring him Saturday",
        description=(
            "Ever fixed a typo and made it worse?\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary), Sarah (Priya) and Jessica (Deb), "
            "lip-synced to their words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, Sarah and Jessica. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#autocorrect", "#texting", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Your lasagna.", 2.0, "Collage"),
    ),
    tags=Tags(
        "everyday-tech",
        "protagonist",
        "embarrassment",
        recurring=("gary", "priya", "deb"),
        test="sp-hook_motion",
        arm="b",
    ),
    style="Collage",
    comedy=Scores(author=18, reviewer=19),
    parts={
        "collage-bubble": 1,
        "collage-deb": 1,
        "collage-dining-room": 1,
        "collage-gary": 1,
        "collage-jun": 1,
        "collage-living-room": 1,
        "collage-omar": 1,
        "collage-phone": 1,
        "collage-priya": 1,
        "collage-sign": 1,
        "collage-tablecloth": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        # collage-lasagna is drawn too; it stays out until it is approved: a release cannot pin a proposed version.
    },
)
