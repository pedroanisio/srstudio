"""The release of gloss-terms."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-terms",
    InstagramPost(
        title="Did anyone actually read the new terms of existence?",
        description=(
            "The Plaza has updated its terms of existence. Tamsin accepts without reading. Section four: hope is now "
            "a premium feature, and declining has been added to section four. By continuing to exist, you agree to "
            "continue existing.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, voiced "
            "with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and Laura (Tamsin); the Plaza "
            "and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=("#termsandconditions", "#fineprint", "#adulting", "#corporatelife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Hope is\npremium", 11.5, "Gloss 07", (540, 960), 1.0),
    ),
    cover=True,
    characters={"gloss-gus": 1, "gloss-nadia": 1, "gloss-sunny": 1, "gloss-tamsin": 1},
)
