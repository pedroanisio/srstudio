"""The release of whats-your-split."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "whats-your-split",
    InstagramPost(
        title="Is that cardio or dread?",
        description=(
            "Is that cardio or dread?\n"
            "A Stick sketch voiced with ElevenLabs premade voices Callum (the trainer) and Roger (the member); every "
            "character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Callum and Roger. Sound effects with ElevenLabs.",
        hashtags=("#smartwatch", "#anxiety", "#gymlife", "#relatable", "#animatedshorts"),
        thumbnail=Thumbnail("What's\nyour split?", 5.0, "Stick", (540, 960), 1.0, place="bottom"),
    ),
    cover=True,
    tags=Tags("everyday-tech", "protagonist", "recognition", test="sp-hook_motion", arm="b"),
    style="Stick",
    comedy=Scores(author=18, reviewer=16),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-gym": 1,
        "stick-gym-counter": 1,
        "stick-handset": 1,
        "stick-message-insert": 1,
        "stick-rig": 1,
        "stick-words": 1,
    },
)
