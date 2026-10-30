"""The release of employee-survey."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "employee-survey",
    InstagramPost(
        title="Anonymous employee survey.",
        description=(
            "Would you recommend working for this company? Not a chance in hell. Then the survey asks for a "
            "department, a job title, a start date and a seat on the office map.\n"
            "Recreation of the.nope.cat's survey reel in the Toon style: a flat cartoon cat whose expression swaps "
            "per line, each phrase in a white pill, and a new synthesised narration. Character, dialogue and "
            "captions are adapted from the reference; the original creator retains rights."
        ),
        credit="Narration: ElevenLabs premade voice Brian. Reference: the.nope.cat.",
        hashtags=(
            "#employeesurvey",
            "#anonymous",
            "#officehumor",
            "#workcomedy",
            "#catsofinstagram",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Anonymous\nsurvey?", 37.0, "Employee survey", (480, 1050), 1.3),
    ),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-cat": 1,
        "toon-desk": 1,
        "toon-room": 1,
    },
)
