"""The release of gloss-exit."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gloss-exit",
    InstagramPost(
        title="What is really behind the exit door?",
        description=(
            "Forty years Gus has looked for this door. Behind it: another door. Then a smaller door. Then a waiting "
            "room, a ticket and a display. He is four million and six. Now serving: three. Waiting is the "
            "attraction.\nA Gloss sketch, a satire of cheerful forever-worlds hosted by a deadpan orb, voiced with "
            "ElevenLabs premade voices Alice (Sunny) and Bill (Gus); the Plaza and every character are original, "
            "drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Alice and Bill. Sound effects generated with ElevenLabs. Music "
            "composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=("#waitingroom", "#bureaucracy", "#customerservice", "#adulting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Behind the\nexit door", 18.5, "Gloss 05", (540, 960), 1.0),
    ),
    cover=True,
)
