"""The release of split-it."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "split-it",
    InstagramPost(
        title="Should we just split it evenly?",
        description=(
            "Mia had a side salad. Brock had the lobster; same thing, basically. Three lobsters, and the wine was for "
            "the table. Then his card is declined, and he promises to send his half tonight.\n"
            "Toon 10: Brock and Mia at the bistro, a new restaurant set, table and card reader."
        ),
        credit="Voices: ElevenLabs premade voices Roger (Brock) and River (Mia). Buzz and sting synthesised.",
        hashtags=(
            "#splitthebill",
            "#datenight",
            "#friendshumor",
            "#moneyhumor",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("Split it\nevenly?", 1.2, "Toon 10", (470, 1130), 1.35),
    ),
    characters={"toon-bear": 1, "toon-rabbit": 1},
)
