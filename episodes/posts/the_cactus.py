"""The release of the-cactus.

Departures from the backlog script (docs/backlog, script 3), accepted by the orchestrator on 2026-10-29: no door
in the office set (the chair's creak marks the interviewer's return), the counter beside the coffee instead of a
tip jar, the last question asked from the applicant's chair with the cactus over his shoulder, then the bloom.
"""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-cactus",
    InstagramPost(
        title="Has this always been here?",
        description=(
            "The interviewer finally notices the cactus on his desk. It came with the chair. Then it is in the café, "
            "by the coffee. Then on the park bench, before you get there. Then in the executive chair. It has an "
            "employee number.\n"
            "Comedy Cut 21: it has been in every video since Five Years. Go and check."
        ),
        credit="Voices: ElevenLabs premade voices Eric, Will, Jessica and Liam. Sound effects generated with "
        "ElevenLabs.",
        hashtags=(
            "#jobinterview",
            "#officehumor",
            "#easteregg",
            "#plantsofinstagram",
            "#animatedshorts",
            "#cartoon",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Has this always\nbeen here?", 1.94, "Comedy Cut 21"),  # his eyes on it; headline below
    ),
    cover=True,
    tags=Tags("job-hunting", "other-person", "recognition", recurring=("cactus", "interviewer", "ava", "milo")),
    parts={
        "barista": 1,
        "bean-jar": 1,
        "bench": 1,
        "building": 1,
        "cafe": 1,
        "cafe-window": 1,
        "candidate": 1,
        "candidate-back": 1,
        "captions": 1,
        "chair": 1,
        "chair-back": 1,
        "coffee-cup": 1,
        "customer": 1,
        "espresso-machine": 1,
        "laptop": 1,
        "location-slate": 1,
        "manager": 1,
        "menu-board": 1,
        "office-art": 1,
        "office-desk": 1,
        "office-reverse": 1,
        "office-wide": 1,
        "papers": 1,
        "park": 1,
        "park-sign": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "pigeon": 1,
        "plant": 1,
        "shrub": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "tree": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
)
