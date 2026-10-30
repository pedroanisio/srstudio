"""The release of gloss-orientation."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-orientation",
    InstagramPost(
        title="Ever woken up inside a mandatory team-building exercise?",
        description=(
            "Day one in the Plaza. Nadia asks for the exit; Sunny says it is right behind her. It is painted on. "
            "Tamsin tried it for eleven years, and Gus is still on his free trial. The exit is available in a future "
            "update.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, voiced with "
            "ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and Laura (Tamsin); the Plaza and "
            "every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Sound effects generated with ElevenLabs."
            " Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#teambuilding", "#corporatelife", "#officehumor", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Where is\nthe exit?", 15.0, "Gloss 01", (540, 960), 1.0),
    ),
    cover=True,
    parts={
        "gloss-board": 1,
        "gloss-door": 1,
        "gloss-gus": 1,
        "gloss-hook": 1,
        "gloss-nadia": 1,
        "gloss-notice": 1,
        "gloss-plaza": 1,
        "gloss-sunny": 1,
        "gloss-tamsin": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
