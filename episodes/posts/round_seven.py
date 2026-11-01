"""The release of round-seven."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "round-seven",
    InstagramPost(
        title="How many interview rounds is too many?",
        description=(
            "Twelve years on the wall and still not hired.\nA Cutout sketch on Okayville, voiced with ElevenLabs "
            "premade voices Jessica (Ava), Will (the Candidate) and Eric (the Boss); every character is original,"
            " drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica, Will and Eric. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobsearch', '#interview', '#jobhunting', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Another interview", 14.6, number=203),
    ),
    tags=Tags("job-hunting", "institution", "recognition", test="sp-speakers", arm="b"),
    style="Cutout",
    parts={},
    comedy=Scores(author=16, reviewer=16),
    cover=True,
)
