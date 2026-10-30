"""The release of still-typing."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "still-typing",
    InstagramPost(
        title="She's been typing for ten minutes. What did I do?",
        description=(
            "Brock asked Mia about pizza. Ten minutes of 'Mia is typing...' later, he has apologised for her plant, "
            "her toothbrush and her mom, who thinks they're engaged. She was choosing a topping.\n"
            "A Toon sketch with Brock and Mia, voiced with ElevenLabs premade voices Roger and River; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Roger (Brock) and River (Mia). Keyboard, buzz and sting synthesised.",
        hashtags=(
            "#typing",
            "#textingproblems",
            "#relationshiphumor",
            "#overthinking",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Mia is typing...\nfor ten minutes", 0.5, "Toon 18"),
    ),
    tags=Tags(
        "everyday-tech", "protagonist", "embarrassment", recurring=("brock", "mia"), test="sp-hook_motion", arm="a"
    ),
)
