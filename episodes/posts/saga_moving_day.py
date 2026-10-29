"""The release of saga-moving-day."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-moving-day",
    InstagramPost(
        title="What does it really cost to own a ship?",
        description=(
            "Juno is moving. It's just a few boxes. And a couch. And her aunt's water tower. And her aunt. To the "
            "top floor of the battle cube, where the lift is broken. Rook owns a ship. He will never fly it "
            "anywhere he wants again.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), River (Juno) and Roger (Rook); the Directorate and every character are "
            "original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, River and Roger. Music composed with ElevenLabs Music. "
            "Original characters, drawn in code."
        ),
        hashtags=(
            "#movingday",
            "#friendswithacar",
            "#moving",
            "#adulting",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("What does it cost\nto own a ship?", 9.0, "Saga 10", (540, 890), 1.0),
    ),
    cover=True,
)
