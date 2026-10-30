"""The release of first-date."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "first-date",
    InstagramPost(
        title='First date. What do you do?',
        description=(
            "Deb asks Jun what he does. He makes a kids' show. She doesn't let her son watch that stuff. It's Bowl "
            "Heads, the toilet thing: thirty billion views. Her son calls. She wants one autograph, then she's "
            'leaving.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Jessica (Deb), Will (Jun) and River (Kai), '
            'lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Jessica, Will and River. Original characters, drawn in code. Sound '
            'effects synthesised in code.'
        ),
        hashtags=("#firstdate", "#dating", "#datinglife", "#brainrot", "#parenting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("First date.\nWhat do you do?", 9.3, "Collage 03", (540, 1090), 1.3),
    ),
    characters={"collage-deb": 1, "collage-jun": 1, "collage-kai": 1},
)
