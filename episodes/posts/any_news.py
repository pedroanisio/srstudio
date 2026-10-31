"""The release of any-news."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "any-news",
    InstagramPost(
        title="Are you seeing anyone?",
        description=(
            "Dinner at Mom's starts with questions. It ends with someone else's secret.\nA Collage sketch on "
            "Okayville, voiced with ElevenLabs premade voices Jessica (Deb), Brian (Brent), Matilda (Rosa) and "
            "Chris (Gary); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, Brian, Matilda and Chris. Original characters, drawn in "
            "code. Sound effects synthesized in code."
        ),
        hashtags=('#familydinner', '#siblings', '#holidays', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("No\ncomment.", 2.0, "Okayville"),
    ),
    tags=Tags(
        "family", "other-person", "tension", recurring=('brent', 'gary', 'rosa', 'deb'), test="sp-hook_motion", arm="b"
    ),
    style="Collage",
    parts={
        # collage-fork, collage-gravy-boat, collage-wine-glass also drawn: a release cannot pin a proposed
        # version, so they join once approved.
        "collage-arm": 1,
        "collage-brent": 1,
        "collage-deb": 1,
        "collage-dining-room": 1,
        "collage-flash": 1,
        "collage-gary": 1,
        "collage-rosa": 1,
        "collage-tablecloth": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=15, reviewer=17),
)
