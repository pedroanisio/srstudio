"""The release of gloss-feedback."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-feedback",
    InstagramPost(
        title="Ever been asked to rate a place you can never leave?",
        description=(
            "The eternal stay survey: one to five. Tamsin gives five forever. Gus gives zero, which is not an option,"
            " so it is recorded as one. Comments go straight into the bin. Based on your feedback, the Plaza has "
            "added more plaza, which was the complaint.\nA Gloss sketch, a satire of cheerful forever-worlds hosted "
            "by a deadpan orb, voiced with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and "
            "Laura (Tamsin); the Plaza and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=("#customersurvey", "#feedback", "#customerexperience", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Rate your\neternal stay", 21.5, "Gloss 04", (540, 960), 1.0),
    ),
    cover=True,
    characters={"gloss-gus": 1, "gloss-nadia": 1, "gloss-sunny": 1, "gloss-tamsin": 1},
)
