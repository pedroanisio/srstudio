"""The release of only-your-aunt."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "only-your-aunt",
    InstagramPost(
        title="Who did your mom tell?",
        description=(
            "One interview, and the whole town wished him luck.\nA Cutout sketch on Okayville, voiced with "
            "ElevenLabs premade voices Liam (Milo) and Lily (Rosa); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam and Lily. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#mom', '#jobinterview', '#family', '#relatable', '#okayville'),
        thumbnail=ShowCover("Don't tell anyone", 3.4, number=193),
    ),
    tags=Tags(
        "job-hunting",
        "other-person",
        "embarrassment",
        test="sp-speakers",
        arm="a",
        send_to="your mom",
        send_line="Nobody! Your aunt doesn't count.",
    ),
    style="Cutout",
    parts={},
    comedy=Scores(author=17, reviewer=18),
    cover=True,
)
