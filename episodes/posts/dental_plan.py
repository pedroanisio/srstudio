"""The release of dental-plan."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "dental-plan",
    InstagramPost(
        title="Why can't you be more like your father? Saga #19",
        description=(
            "However far you go, the family keeps score, and the relative with benefits is ahead.\nA Saga sketch "
            "on Okayville, voiced with ElevenLabs premade voices Lily (Mabel), River (Juno) and George (the "
            "narrator); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Lily, River and George. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#spaceopera', '#grandma', '#familyhumor', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("He has a dental plan", 21.6, number=206, series="Saga", series_number=19),
    ),
    tags=Tags("epic-world", "other-person", "recognition", test="sp-speakers", arm="a"),
    style="Saga",
    parts={},
    comedy=Scores(author=16, reviewer=15),
    cover=True,
)
