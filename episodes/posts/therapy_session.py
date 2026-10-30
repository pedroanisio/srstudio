"""The release of therapy-session."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "therapy-session",
    InstagramPost(
        title='Why are you here today?',
        description=(
            "Jun made a show about a toilet. It's his most successful work. He went to film school for this. Feld's "
            'session is two hundred dollars. Can he pay in exposure? Thirty billion views. Same time next week: bring '
            'the toilet.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Alice (Feld) and Will (Jun), lip-synced to their '
            'words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Alice and Will. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#therapy", "#creativelife", "#filmschool", "#brainrot", "#burnout", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Why are you\nhere today?", 14.8, "Collage 07", (540, 1090), 1.3),
    ),
    characters={"collage-feld": 1, "collage-jun": 1},
)
