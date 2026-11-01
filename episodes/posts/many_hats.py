"""The release of many-hats."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "many-hats",
    InstagramPost(
        title="How many jobs is one job now?",
        description=(
            "The fourth one was still warm.\nA Cutout sketch on Okayville, voiced with ElevenLabs premade voices "
            "Eric (the Boss) and Will (the Candidate); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Eric and Will. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#jobsearch', '#jobhunting', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("One position", 13.0, number=195),
    ),
    tags=Tags("job-hunting", "institution", "recognition", test="sp-speakers", arm="a"),
    style="Cutout",
    parts={},
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
