"""The release of saga-on-hold."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-on-hold",
    InstagramPost(
        title="Who do you call when your planet gets destroyed?",
        description=(
            "Juno's planet was destroyed. Has she tried restarting it? Please hold. Can she speak to a human? All "
            "their humans were on her planet. Would she like to add planet insurance?\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), River (Juno) and Jessica (the droid); the Directorate and every character "
            "are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, River and Jessica. Sound effects generated with ElevenLabs. "
            "Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#onhold",
            "#customerservice",
            "#callcenter",
            "#adulting",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Planet destroyed?\nWho do you call?", 12.0, "Saga 12", (540, 890), 1.0),
    ),
    cover=True,
)
