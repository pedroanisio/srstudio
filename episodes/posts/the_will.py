"""The release of the-will."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-will",
    InstagramPost(
        title="Why wait until I'm dead to read my will?",
        description=(
            "Rosa reads her will now, to watch their faces. The house goes to Gary, if he finishes one book that "
            "isn't about a toilet. Everything else goes to Kai, if he can name one thing that isn't a toilet.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa), Chris (Gary) and River (Kai), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda, Chris and River. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#inheritance", "#family", "#grandma", "#brainrot", "#parenting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Why wait until\nI'm dead?", 1.0, "Collage 09", (540, 1200), 1.6),
    ),
    characters={"collage-gary": 1, "collage-kai": 1, "collage-rosa": 1},
)
