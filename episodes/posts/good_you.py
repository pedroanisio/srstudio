"""The release of good-you."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "good-you",
    InstagramPost(
        title="How was your weekend?",
        description=(
            "Good, you? Good. Nothing has ever happened to anyone in the history of the office kitchen.\n"
            "Stick 12: one coffee machine, one window, a very long year of Mondays, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Roger and River. Sound effects with ElevenLabs.",
        hashtags=("#mondays", "#officelife", "#smalltalk", "#deadpan", "#stickfigure", "#animatedshorts"),
        thumbnail=Thumbnail("How was\nyour\nweekend?", 0.5, "Stick 12", (540, 860), 1.0, place="top"),
    ),
    cover=True,
    tags=Tags("office", "protagonist", "recognition", test="sp-hook_motion", arm="a", recipient="b", to="work friend"),
    style="Stick",
    parts={"signature-cactus": 1, "signature-code": 1, "stick-card": 1, "stick-rig": 1, "stick-words": 1},
)
