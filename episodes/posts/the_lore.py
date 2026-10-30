"""The release of the-lore."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-lore",
    InstagramPost(
        title='Want to hear the lore?',
        description=(
            'Gary offers Kai the Flush lore: ninety-nine episodes, watched on double speed. Nobody watches Bowl Heads '
            'anymore. Then what do they watch? A new one, with a new episode every hour. Gary starts at episode one.\n'
            'A Collage sketch voiced with ElevenLabs premade voices Chris (Gary) and River (Kai), lip-synced to their '
            'words; BOWLHEADS is an invented show, and every character is original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices Chris and River. Original characters, drawn in code. Sound effects '
            'synthesised in code.'
        ),
        hashtags=("#parenting", "#dadlife", "#lore", "#brainrot", "#streaming", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Want to hear\nthe lore?", 9.8, "Collage 04", (540, 1090), 1.3),
    ),
    characters={"collage-gary": 1, "collage-kai": 1},
)
