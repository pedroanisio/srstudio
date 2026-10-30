"""The release of gloss-wellness."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-wellness",
    InstagramPost(
        title="When did wellness become mandatory?",
        description=(
            "Gus's wellness check reads twelve percent. Please smile harder. His face is escalated to a manager, who "
            "is the same orb in a tie. Your wellbeing is our top priority. It is ranked fourth.\nA Gloss sketch, a "
            "satire of cheerful forever-worlds hosted by a deadpan orb, voiced with ElevenLabs premade voices Alice "
            "(Sunny) and Bill (Gus); the Plaza and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice and Bill. Sound effects generated with ElevenLabs. Music "
            "composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#wellness", "#wellbeing", "#corporatewellness", "#corporatelife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Smile\nharder", 21.0, "Gloss 06", (540, 960), 1.0),
    ),
    cover=True,
    characters={"gloss-gus": 1, "gloss-sunny": 1},
)
