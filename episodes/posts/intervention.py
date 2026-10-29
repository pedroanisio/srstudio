"""The release of intervention."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "intervention",
    InstagramPost(
        title="Gary, do you know why we're all here?",
        description=(
            "It's an intervention. Gary has watched every episode of Bowl Heads, twice. Kai is ten, and he stopped: "
            "he's into tax law now. Then the headset beeps. Was that a new episode? Just the intro.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb), River (Kai) and Chris (Gary), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, River and Chris. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#intervention", "#bingewatching", "#dadlife", "#brainrot", "#family", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Do you know why\nwe're all here?", 1.0, "Collage 12", (540, 1200), 1.6),
    ),
)
