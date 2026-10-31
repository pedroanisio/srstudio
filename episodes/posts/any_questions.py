"""The release of any-questions."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "any-questions",
    InstagramPost(
        title="Do you have any questions for us?",
        description=(
            "There is one honest question in a job interview. Nobody has ever asked it and stayed in the chair "
            "they came in with.\nA Cutout sketch on Okayville, voiced with ElevenLabs premade voices Eric (the "
            "manager) and Will (the candidate); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Eric and Will. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#jobinterview', '#jobhunting', '#careerhumor', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Are you\nhappy here?", 4.0, "Okayville"),
    ),
    tags=Tags("job-hunting", "other-person", "triumph", test="sp-hook_motion", arm="a"),
    style="Cutout",
    cover=True,
    parts={
        # cv-folder also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "hiring-office": 1,
        "manager": 1,
        "office-reverse": 1,
        "papers": 1,
        "roller-blind": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
    comedy=Scores(author=16, reviewer=19),
)
