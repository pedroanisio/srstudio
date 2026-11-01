"""The release of exciting-opportunity."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "exciting-opportunity",
    InstagramPost(
        title="Why can't the recruiter ever say?",
        description=(
            "Six years, and nobody has told him.\nA Collage sketch on Okayville, voiced with ElevenLabs premade "
            "voices Sarah (Priya), Jessica (Deb) and Brian (Brent); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah, Jessica and Brian. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#jobsearch', '#recruiters', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("He can't say", 12.2, number=197),
    ),
    tags=Tags("job-hunting", "other-person", "recognition", test="sp-speakers", arm="b"),
    style="Collage",
    parts={
        "collage-brent": 1,
        "collage-deb": 1,
        "collage-living-room": 1,
        "collage-phone": 1,
        "collage-priya": 1,
        "collage-sign": 1,
        "collage-sofa": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=16, reviewer=15),
    cover=True,
)
