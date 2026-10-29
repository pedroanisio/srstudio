"""The release of unexpected-item."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "unexpected-item",
    InstagramPost(
        title="Unexpected item in the bagging area.",
        description=(
            "One avocado. The machine wanted it in the bagging area, then out of it, then back in it, then called "
            "for help. Two hundred items scanned and bagged this month, three jams fixed: congratulations, you're "
            "employee of the month.\n"
            "Stick 04: Dev at the self-checkout, a store and a kiosk drawn in code, the captions one word at a time."
        ),
        credit="Voices: ElevenLabs premade voices Laura, Will and Alice. Sound effect and instrumental music composed "
        "with ElevenLabs.",
        hashtags=(
            "#selfcheckout",
            "#unexpecteditem",
            "#grocerystore",
            "#adulting",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Employee of\nthe month.", 24.3, "Stick 04", (540, 1200), 1.3),
    ),
    cover=True,
)
