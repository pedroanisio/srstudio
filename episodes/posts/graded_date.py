"""The release of graded-date."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "graded-date",
    InstagramPost(
        title="First date with a teacher. Every answer gets a grade.",
        description=(
            "Gary is on a first date with Priya, and her red pen is out. Hiking: C. The book he is reading: D. "
            "Then he does the voice from his kid's toilet show, and she writes one more thing.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary) and Sarah (Priya), lip-synced to "
            "their words; BOWLHEADS is an invented show, and every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris and Sarah. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#firstdate", "#dating", "#teacherlife", "#datingover40", "#brainrot", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("What do you\ndo for fun?", 0.5, "Collage 14", (600, 1000), 1.3, place="bottom"),
    ),
    tags=Tags("relationships", "protagonist", "affection", recurring=("gary", "priya"), test="sp-hook_motion", arm="a"),
)
