"""The release of sinking-chair."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "sinking-chair",
    InstagramPost(
        title="Has your chair ever done this in a meeting?",
        description=(
            "Three years. He's never said a word."
            "\n"
            "A Cutout sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will (the Candidate) and Eric (the Boss). Foley synthesized.",
        hashtags=("#office", "#performancereview", "#relatable", "#animatedshorts", "#comedyshorts"),
        thumbnail=Thumbnail("Has your chair\never done this?", 5.9, "Okayville"),
    ),
    cover=True,
    tags=Tags(
        "office",
        "institution",
        "embarrassment",
        recurring=("candidate", "manager"),
        test="sp-hook_motion",
        arm="b",
        recipient="a",
    ),
    style="Cutout",
    parts={
        "ballpoint": 1,
        "candidate": 1,
        "captions": 1,
        "chair": 1,
        "chair-lever": 1,
        "laptop": 1,
        "manager": 1,
        "office-art": 1,
        "office-desk": 1,
        "office-reverse": 1,
        "papers": 1,
        "plant": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "squeak-mark": 1,
        "water-glass": 1,
        "woodgrain": 1,
    },
    comedy=Scores(18, 18),
)
