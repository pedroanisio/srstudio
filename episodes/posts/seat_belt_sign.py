"""The release of seat-belt-sign."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "seat-belt-sign",
    InstagramPost(
        title="Why does everyone stand up when the plane lands?",
        description=(
            "Twenty minutes bent under a bin to win nothing."
            "\n"
            "A Stick sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica (Noor), Will (Dev) and Alice (the announcement). "
            "Foley synthesized."
        ),
        hashtags=('#travel', '#airplane', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Why are you\nstanding?", 3.0, "Stick 22", place="top"),
    ),
    cover=True,
    tags=Tags(
        "relationships",
        "protagonist",
        "triumph",
        recurring=("dev", "noor"),
        test="sp-hook_motion",
        arm="a",
        recipient="b",
        to="partner",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-cabin": 1,
        "stick-card": 1,
        "stick-carry-on": 1,
        "stick-rig": 1,
        "stick-words": 1,
    },
    comedy=Scores(17, 18),
)
