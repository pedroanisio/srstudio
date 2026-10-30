"""The release of neighbor-names."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "neighbor-names",
    InstagramPost(
        title="Seven years sharing an elevator with your neighbor, and you never asked her name.",
        description=(
            "Now it is far too late to ask. He tries anyway, and asks about her cardigan instead. Then the doors "
            "open on someone who knows both their names. Or says he does.\n"
            "Comedy Cut 25: Rosa, new in the building, and the applicant from Five Years, on the way down."
        ),
        credit="Voices: ElevenLabs premade voices Lily, Will and Eric. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#neighbors",
            "#awkward",
            "#elevator",
            "#smalltalk",
            "#everydaylife",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Seven years.\nNo names.", 5.5, "Comedy Cut 25"),  # the silence, before the doors
    ),
    cover=True,
    tags=Tags(
        "relationships",
        "protagonist",
        "embarrassment",
        recurring=("candidate", "manager"),
        test="sp-hook_motion",
        arm="b",
    ),
    characters={"candidate": 1, "manager": 1, "rosa": 1},
)
