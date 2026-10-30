"""The release of final-broadcast."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "final-broadcast",
    InstagramPost(
        title="After thirty years, is this really my last broadcast?",
        description=(
            "Omar's last night on air. The network found a younger anchor: Flush, the singing toilet. He tested "
            "great with young people. He can't even read the news. Neither can the viewers. And now, the weather.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Daniel (Omar), Will (Jun) and Charlie (Flush), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Daniel, Will and Charlie. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#news", "#newsanchor", "#replaced", "#brainrot", "#media", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Is this my last\nbroadcast?", 1.0, "Collage 11", (540, 1200), 1.6),
    ),
    characters={"collage-flush": 1, "collage-jun": 1, "collage-omar": 1},
)
