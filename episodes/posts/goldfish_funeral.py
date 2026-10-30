"""The release of goldfish-funeral."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "goldfish-funeral",
    InstagramPost(
        title="Do you want to say a few words for Bubbles?",
        description=(
            "Gary and Kai say goodbye to Bubbles the goldfish. He was a good fish. A great fish. Then the toilet "
            "answers: Flush, the singing toilet from the show, is in every toilet. Gary asks for a selfie.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary), River (Kai) and Charlie (Flush), "
            "lip-synced to their words; BOWLHEADS is an invented show, and every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, River and Charlie. Original characters, drawn in code. Sound "
            "effects synthesised in code."
        ),
        hashtags=("#goldfish", "#parenting", "#petfuneral", "#brainrot", "#dadlife", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("A few words\nfor Bubbles?", 1.0, "Collage 08", (540, 1200), 1.6),
    ),
    characters={"collage-flush": 1, "collage-gary": 1, "collage-kai": 1},
)
