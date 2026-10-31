"""The release of you-have-it."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "you-have-it",
    InstagramPost(
        title="Who eats the last slice?",
        description=(
            "Nobody takes the last slice. It is not generosity. It is war."
            "\n"
            "A Collage sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Sarah (Priya) and Jessica (Deb). Foley synthesized.",
        hashtags=('#lastslice', '#friends', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("You have it.", 14.9, "Collage 30"),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "tension",
        recurring=("priya", "deb"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="best friend",
    ),
    style="Collage",
    parts={
        "collage-cafe": 1,
        "collage-cake-slice": 1,
        "collage-deb": 1,
        "collage-flash": 1,
        "collage-gust": 1,
        "collage-priya": 1,
        "collage-tablecloth": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(19, 19),
)
