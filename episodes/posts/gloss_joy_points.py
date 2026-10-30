"""The release of gloss-joy-points."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-joy-points",
    InstagramPost(
        title="What if every tiny thing you did was being scored?",
        description=(
            "Gus holds a door: plus two. Gus breathes, heavily: minus. Tamsin has nine million Joy Points and is "
            "saving up for more points, because points can be redeemed for more points. The balance does not roll "
            "over. Neither do you.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, "
            "voiced with ElevenLabs premade voices Alice (Sunny), Bill (Gus) and Laura (Tamsin); the Plaza and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Bill and Laura. Music composed with ElevenLabs Music. Original "
            "characters, drawn in code."
        ),
        hashtags=("#gamification", "#performancereview", "#kpi", "#corporatelife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Points for\nmore points", 15.8, "Gloss 02", (540, 960), 1.0),
    ),
    cover=True,
    characters={"gloss-gus": 1, "gloss-sunny": 1, "gloss-tamsin": 1},
)
