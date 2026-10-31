"""The release of dont-move."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "dont-move",
    InstagramPost(
        title="How far back have you scrolled?",
        description=(
            "She talked him six years into a stranger's photos with a steady hand. The hand was the easy part.\nA "
            "Cutout sketch on Okayville, voiced with ElevenLabs premade voices Jessica (Ava) and Liam (Milo); "
            "every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica and Liam. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#socialmedia', '#instagramfails', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Don't\nbreathe.", 12.0, "Okayville", focus=(690.0, 1040.0), zoom=1.45),
    ),
    tags=Tags("own-worst-enemy", "protagonist", "tension", test="sp-hook_motion", arm="b"),
    style="Cutout",
    cover=True,
    parts={
        # big-thumb, cafe-door, coat-over, phone-post also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "barista": 1,
        "bean-jar": 1,
        "cafe": 1,
        "cafe-window": 1,
        "captions": 1,
        "coffee-cup": 1,
        "customer": 1,
        "espresso-machine": 1,
        "gold-watch": 1,
        "menu-board": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=14, reviewer=19),
)
