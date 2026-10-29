"""The release of the-family-photo."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-family-photo",
    InstagramPost(
        title="Ten seconds! Natural!",
        description=(
            "Gary wants one natural family photo, so he directs every face on the sofa until nobody looks natural. "
            "With seconds left, he tries one last thing.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary), Matilda (Rosa) and River (Kai), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, Matilda and River. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#familyphoto", "#family", "#dadlife", "#brainrot", "#parenting", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Everyone,\nbe natural.", 5.0, "Collage 13", (540, 1300), 1.2),
    ),
    tags=Tags("family", "protagonist", "embarrassment", recurring=("gary", "rosa", "kai")),
)
