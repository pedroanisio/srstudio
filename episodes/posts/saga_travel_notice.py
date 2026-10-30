"""The release of saga-travel-notice."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-travel-notice",
    InstagramPost(
        title="The most feared man in the galaxy, frozen out by his bank over one coffee",
        description=(
            "Lord Gloom orders a small coffee on a trip. Card declined. Again. Then a fraud alert: was this you? "
            "Yes. Thank you: for your safety, the card is now frozen. The bar also takes cash, or dishes.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Jessica (the bar droid) and Callum (Lord Gloom); the Directorate and every "
            "character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Jessica and Callum. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#fraudalert", "#carddeclined", "#banking", "#travel", "#spaceopera", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Card frozen\nfor buying coffee", 9.6, "Saga 16", (540, 890), 1.0),
    ),
    cover=True,
    tags=Tags(
        "money-services", "institution", "embarrassment", recurring=("gloom", "droid"), test="sp-hook_motion", arm="b"
    ),  # fmt: skip
    characters={"saga-droid": 1, "saga-gloom": 1},
)
