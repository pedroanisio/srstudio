"""The release of book-report."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "book-report",
    InstagramPost(
        title='A book report about a toilet?',
        description=(
            "Priya asks why Kai's book report is about a toilet. Gary says it's not a toilet, it's Flush, and he has a"
            ' whole arc. Season two is basically Moby Dick. Kai got a D. Gary would like to speak to its manager.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Sarah (Priya) and Chris (Gary), lip-synced to '
            'their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Sarah and Chris. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#parenting", "#homework", "#schoollife", "#brainrot", "#dadlife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("A book report\nabout a toilet?", 16.8, "Collage 02", (540, 1090), 1.3),
    ),
    parts={
        "collage-classroom": 1,
        "collage-gary": 1,
        "collage-priya": 1,
        "collage-sign": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
