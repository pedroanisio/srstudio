"""The release of gloss-fewer-meetings."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-fewer-meetings",
    InstagramPost(
        title="Who is ready for our meeting about having fewer meetings?",
        description=(
            "The Plaza takes the feedback: fewer meetings. So there is a meeting about it, and a meeting about "
            "emails, and an agenda whose only item is the next meeting. Everyone agrees there are too many. "
            "Wonderful: a follow up.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, "
            "voiced with ElevenLabs premade voices Alice (Sunny), Sarah (Nadia), Bill (Gus) and Laura (Tamsin); the "
            "Plaza and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=("#meetings", "#corporatelife", "#officehumor", "#worklife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("This meeting\nnever ends", 12.0, "Gloss 08", (540, 960), 1.0),
    ),
    cover=True,
    tags=Tags(
        "office",
        "institution",
        "recognition",
        recurring=("sunny", "nadia", "gus", "tamsin"),
        test="sp-hook_motion",
        arm="a",
    ),
    characters={"gloss-gus": 1, "gloss-nadia": 1, "gloss-sunny": 1, "gloss-tamsin": 1},
)
