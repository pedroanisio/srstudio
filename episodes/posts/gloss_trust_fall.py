"""The release of gloss-trust-fall."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-trust-fall",
    InstagramPost(
        title="How much should you trust your workplace?",
        description=(
            "Today's activity is a trust fall. Nadia asks who is catching her. Sunny says: trust. Nobody catches her;"
            " catching was not in the budget. Gus fell in March and is still waiting for the trust. Please remain on "
            "the floor for scoring.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, "
            "voiced with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia) and Bill (Gus); the Plaza and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah and Bill. Sound effects generated with ElevenLabs. Music "
            "composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#teambuilding", "#trustfall", "#corporatelife", "#workculture", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Who is\ncatching me?", 7.6, "Gloss 03", (540, 960), 1.0),
    ),
    cover=True,
    parts={
        "gloss-activity": 1,
        "gloss-board": 1,
        "gloss-gus": 1,
        "gloss-hook": 1,
        "gloss-nadia": 1,
        "gloss-notice": 1,
        "gloss-sunny": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
