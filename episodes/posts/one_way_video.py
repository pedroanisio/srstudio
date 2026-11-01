"""The release of one-way-video."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "one-way-video",
    InstagramPost(
        title="Who are you smiling at in a video interview?",
        description=(
            "He had cereal and better eye contact.\nA Cutout sketch on Okayville, voiced with ElevenLabs premade "
            "voices Will (the Candidate), Liam (Milo) and Alice (the System); every character is original, drawn "
            "in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will, Liam and Alice. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobsearch', '#interview', '#videointerview', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Nobody is there", 14.0, number=207),
    ),
    tags=Tags("job-hunting", "institution", "embarrassment", test="sp-speakers", arm="b"),
    style="Cutout",
    parts={},
    comedy=Scores(author=15, reviewer=17),
    cover=True,
)
