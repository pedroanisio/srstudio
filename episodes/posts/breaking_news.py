"""The release of breaking-news."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "breaking-news",
    InstagramPost(
        title="Is a toilet rotting your kid's brain?",
        description=(
            "Omar asks if a singing toilet is rotting your child's brain. Experts say yes. Experts also say it gets "
            "ten times the ratings. So tonight's weather is brought to you by Flush. The ratings just tripled.\n"
            'A Collage sketch voiced with ElevenLabs premade voices Daniel (Omar) and Charlie (Flush), lip-synced to '
            'their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Daniel and Charlie. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#news", "#breakingnews", "#media", "#brainrot", "#ratings", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Is a toilet rotting\nyour kid's brain?", 14.0, "Collage 06", (540, 1090), 1.3),
    ),
    characters={"collage-flush": 1, "collage-omar": 1},
)
