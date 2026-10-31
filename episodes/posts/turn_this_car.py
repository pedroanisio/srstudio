"""The release of turn-this-car."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "turn-this-car",
    InstagramPost(
        title="Did your dad ever actually turn the car around?",
        description=(
            "Every parent has made the threat. This one was five miles from the beach, and he had a hotel booked.\n"
            "A Stick sketch on Okayville, voiced with ElevenLabs premade voices Will (Dad), Jessica (Mom) and River "
            "(Kid); every character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will, Jessica and River. Original characters, drawn in code. Sound "
        "effects with ElevenLabs; the indicator and the engine ticks synthesized in code.",
        hashtags=("#roadtrip", "#parenting", "#familyhumor", "#stickfigure", "#okayville"),
        thumbnail=Thumbnail("One more\nword", 4.9, "Okayville", (540, 860), 1.0, place="top"),
    ),
    cover=True,
    tags=Tags("family", "protagonist", "tension", recurring=("dev", "noor"), test="sp-hook_motion", arm="a"),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-rig": 1,
        "stick-road-ahead": 1,
        "stick-road-plan": 1,
        "stick-road-sign": 1,
        "stick-top-car": 1,
        "stick-windshield": 1,
        "stick-windshield-dash": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=15, reviewer=19),
)
