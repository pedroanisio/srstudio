"""The release of thought-leader."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "thought-leader",
    InstagramPost(
        title="Can I read you my post before it goes live?",
        description=(
            "Brent's new post: what a singing toilet taught him about leadership. Lesson one, always be flushing. "
            "Lesson two, let go of what weighs you down. Jun wrote that show. Lesson four: never credit the writer.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Brian (Brent) and Will (Jun), lip-synced to "
            "their words; BOWLHEADS is an invented show, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Will. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=(
            "#thoughtleadership",
            "#linkedin",
            "#leadership",
            "#brainrot",
            "#creatives",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Can I read you\nmy post?", 1.0, "Collage 10", (540, 1200), 1.6),
    ),
    characters={"collage-brent": 1, "collage-jun": 1},
)
