"""The release of name-a-number."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "name-a-number",
    InstagramPost(
        title="The salary talk: whoever says a number first loses.",
        description=(
            "So he asks what would make you happy, and you ask him the same thing back. The ad said competitive. "
            "Competitive with what? Then you both write it down.\n"
            "Comedy Cut 24: the interviewer and the applicant from Five Years, back across the desk."
        ),
        credit="Voices: ElevenLabs premade voices Eric and Will. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#salarynegotiation",
            "#jobinterview",
            "#jobsearch",
            "#hiring",
            "#worklife",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail("Name a\nnumber.", 10.9, "Comedy Cut 24"),  # "Extremely competitive", before the papers
    ),
    cover=True,
    tags=Tags(
        "job-hunting",
        "other-person",
        "recognition",
        recurring=("manager", "candidate"),
        test="sp-hook_motion",
        arm="a",
    ),
)
