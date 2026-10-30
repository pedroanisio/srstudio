"""The release of the-boxes."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-boxes",
    InstagramPost(
        title="Upload your work history. Now type it all again into the boxes.",
        description=(
            "Priya is applying for a job. Rosa walks her through the form: upload the file, type the file into the "
            "boxes, add a two-page cover letter, submit. The answer takes one second.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa) and Sarah (Priya), lip-synced to "
            "their words; the hiring form is invented, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda and Sarah. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#jobsearch",
            "#jobhunting",
            "#jobapplication",
            "#hiring",
            "#relatable",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Now type it all\nagain into the boxes.", 3.0, "Collage 19", None, 1.0, place="bottom"),
    ),
    tags=Tags("job-hunting", "institution", "recognition", recurring=("rosa", "priya"), test="sp-hook_motion", arm="b"),
    parts={
        "collage-boardroom": 1,
        "collage-classroom": 1,
        "collage-priya": 1,
        "collage-rosa": 1,
        "collage-sign": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
