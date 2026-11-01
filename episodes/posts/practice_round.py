"""The release of practice-round."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "practice-round",
    InstagramPost(
        title="What does your partner always bring up?",
        description=(
            "He said to be tough. He did not mean this tough.\nA Stick sketch on Okayville, voiced with ElevenLabs"
            " premade voices Will (Dev) and Jessica (Noor); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Jessica. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#interviewprep', '#marriage', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Be tough, he said", 6.0, number=196),
    ),
    tags=Tags(
        "job-hunting",
        "other-person",
        "tension",
        recurring=("dev", "noor"),
        test="sp-speakers",
        arm="a",
        send_to="your partner",
        send_line="We'll let you know.",
    ),
    style="Stick",
    parts={},
    comedy=Scores(author=17, reviewer=17),
    cover=True,
)
