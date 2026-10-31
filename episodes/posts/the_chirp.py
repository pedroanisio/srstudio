"""The release of the-chirp."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-chirp",
    InstagramPost(
        title="Which one is it?",
        description=(
            "Which one is it?\n"
            "A Stick sketch voiced with ElevenLabs premade voices Will (the husband) and Jessica (the wife); every "
            "character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Will and Jessica. Sound effects with ElevenLabs and in code.",
        hashtags=("#smokealarm", "#homeowner", "#marriage", "#relatable", "#animatedshorts"),
        thumbnail=Thumbnail("Which\none?", 3.0, "Stick", (540, 960), 1.0, place="bottom"),
    ),
    cover=True,
    tags=Tags("everyday-tech", "protagonist", "tension", test="sp-hook_motion", arm="a"),
    style="Stick",
    comedy=Scores(author=19, reviewer=19),
    parts={
        # Drawn too and proposed, so they stay out until approved: a release cannot pin a proposed version:
        # stick-bedroom, stick-chair, stick-mound, stick-shovel, stick-smoke-alarm.
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-fridge-open": 1,
        "stick-kitchen": 1,
        "stick-rig": 1,
        "stick-words": 1,
        "stick-yard": 1,
    },
)
