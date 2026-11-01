"""The release of book-a-table."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "book-a-table",
    InstagramPost(
        title="Do you rehearse before a phone call?",
        description=(
            "Priya has trained for this. Two lines, one call, Friday at seven.\nA Collage sketch on Okayville, "
            "voiced with ElevenLabs premade voices Sarah (Priya), Jessica (Deb) and Alice (the restaurant); every"
            " character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah, Jessica and Alice. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#phoneanxiety', '#relatable', '#anxiety', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Table for two,\nFriday, seven.", 18.2, "Okayville"),
    ),
    tags=Tags(
        "own-worst-enemy", "protagonist", "embarrassment", recurring=('priya', 'deb'), test="sp-hook_motion", arm="a"
    ),
    style="Collage",
    parts={
        "collage-arm": 1,
        "collage-counter": 1,
        "collage-deb": 1,
        "collage-living-room": 1,
        "collage-phone": 1,
        "collage-priya": 1,
        "collage-ring-corner": 1,
        "collage-sofa": 1,
        "collage-stool": 1,
        "collage-towel": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=16, reviewer=19),
)
