"""The release of what-my-dad-does."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "what-my-dad-does",
    InstagramPost(
        title="Have you read what your kid wrote about you?",
        description=(
            "Parent-teacher night, on a chair built for an eight-year-old. The essay: What My Dad Does. He works "
            "from home, in a tie and no pants. His job is saying \"I think you're on mute\". At three he has Focus "
            "Time, and Focus Time snores. Last line: Dad says he works from home. Mom says he's just home.\n"
            "Stick 07: a classroom, a tiny chair and an essay page drawn in code, the captions one word at a time."
        ),
        credit="Voices: ElevenLabs premade voices Will and Sarah. Sound effect and instrumental music composed with "
        "ElevenLabs.",
        hashtags=(
            "#workfromhome",
            "#parentteacher",
            "#parentinghumor",
            "#remotework",
            "#animatedshorts",
            "#stickfigure",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("What my\ndad does", 18.6, "Stick 07", place="top"),
    ),
    cover=True,
    characters={"stick-rig": 1},
)
