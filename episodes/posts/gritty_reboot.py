"""The release of gritty-reboot."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "gritty-reboot",
    InstagramPost(
        title='Can you give me pain?',
        description=(
            "Jun is taking his toilet show prestige. He asks Flush for pain. Flush flush, yeah? Be sadder: your "
            "father was a urinal. Now look at the camera like you've lost everything. The best acting Jun has seen "
            "all year.\n"
            'A Collage sketch voiced with ElevenLabs premade voices Will (Jun) and Charlie (Flush), lip-synced to '
            'their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Will and Charlie. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#reboot", "#prestigetv", "#acting", "#brainrot", "#filmmaking", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Can you give\nme pain?", 13.5, "Collage 05", (540, 1240), 1.3),
    ),
    parts={
        "collage-flush": 1,
        "collage-jun": 1,
        "collage-sign": 1,
        "collage-stage": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)
