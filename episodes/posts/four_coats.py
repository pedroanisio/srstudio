"""The release of four-coats."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "four-coats",
    InstagramPost(
        title="How many coats is sixty dollars?",
        description=(
            "How many coats is sixty dollars?\n"
            "A Stick sketch voiced with ElevenLabs premade voices Laura (the traveler) and Roger (the agent); every "
            "character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Laura and Roger. Sound effects with ElevenLabs.",
        hashtags=("#airlines", "#baggagefees", "#travel", "#relatable", "#animatedshorts"),
        thumbnail=Thumbnail("For\npoint four?", 18.0, "Stick", (540, 960), 1.0, place="bottom"),
    ),
    cover=True,
    tags=Tags("money-services", "institution", "triumph", test="sp-hook_motion", arm="b"),
    style="Stick",
    comedy=Scores(author=19, reviewer=18),
    parts={
        # stick-bag-scale, stick-coat-ball, stick-palm are drawn too; they stay out until they are approved: a release cannot pin a
        # proposed version.
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-carry-on": 1,
        "stick-gate": 1,
        "stick-gate-podium": 1,
        "stick-rig": 1,
        "stick-words": 1,
    },
)
