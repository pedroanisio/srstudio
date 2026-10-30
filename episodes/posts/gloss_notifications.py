"""The release of gloss-notifications."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-notifications",
    InstagramPost(
        title="Would you like to turn on notifications? No thank you. Ping: you said no thank you.",
        description=(
            "The Plaza asks Gus about notifications, then notifies him that he declined. Tamsin turns on all of "
            "them. Turning them off is coming soon, and you will be notified.\nA Gloss sketch, a satire of cheerful "
            "forever-worlds hosted by a deadpan orb, voiced with ElevenLabs premade voices Alice (Sunny), Sarah "
            "(Nadia), Bill (Gus) and Laura (Tamsin); the Plaza and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice, Sarah, Bill and Laura. Sound effects generated with "
            "ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#notifications", "#smartphone", "#techhumor", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Saying no\nis a ping", 5.0, "Gloss 09", (540, 960), 1.0),
    ),
    cover=True,
    tags=Tags(
        "everyday-tech",
        "institution",
        "recognition",
        recurring=("sunny", "nadia", "gus", "tamsin"),
        test="sp-hook_motion",
        arm="b",
    ),
)
