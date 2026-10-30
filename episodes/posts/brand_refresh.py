"""The release of brand-refresh."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "brand-refresh",
    InstagramPost(
        title='Why is our logo a toilet?',
        description=(
            'Rosa runs a bank. Brent rebranded it after a singing toilet, because that is what the kids watch. Q3 is '
            "down. Brent says it's a song. Rosa asks him to play it again.\n"
            'A Collage sketch voiced with ElevenLabs premade voices Matilda (Rosa), Brian (Brent) and Charlie (Flush),'
            ' lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in '
            'code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Matilda, Brian and Charlie. Original characters, drawn in code. Sound '
            'effects synthesised in code.'
        ),
        hashtags=(
            "#rebrand",
            "#marketing",
            "#corporatelife",
            "#brainrot",
            "#officehumor",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Why is our logo\na toilet?", 16.2, "Collage 01", (540, 1090), 1.3),
    ),
    parts={
        "collage-boardroom": 1,
        "collage-brent": 1,
        "collage-chart": 1,
        "collage-flush": 1,
        "collage-rosa": 1,
        "collage-sign": 1,
        "collage-stage": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
