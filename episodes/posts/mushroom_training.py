"""The release of mushroom-training."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "mushroom-training",
    InstagramPost(
        title="Work training be like.",
        description=(
            "This module will take 45 minutes to complete, and there will be a test at the end. A mushroom sits "
            "through all of it.\n"
            "Recreation of the Under Studio training cartoon in the Cel style: traced drawings, a measured camera "
            "push, hand-lettered captions and a new synthesized narration. Character art, dialogue and lettering "
            "are adapted from the reference; the original creator retains rights."
        ),
        credit="Narration: ElevenLabs premade voice Alice. Reference: understudiohub / Under Studio.",
        hashtags=(
            "#worktraining",
            "#officehumor",
            "#onboarding",
            "#compliancetraining",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Work training\nbe like", 36.0, "Workplace module", (540, 700), 1.3),
    ),
    parts={"cel-lettering": 1, "cel-room": 1, "cel-traced": 1},
)
