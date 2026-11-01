"""The release of extra-hour."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "extra-hour",
    InstagramPost(
        title="What did your extra hour go to?",
        description=(
            "The clocks went back. He has plans for that hour. All of them.\nA Stick sketch on Okayville, voiced "
            "with ElevenLabs premade voices Will (Dev) and Jessica (Noor); every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Jessica. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#daylightsaving', '#fallback', '#marriage', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("The clocks went back", 12.0, number=197),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "recognition",
        recurring=("dev", "noor"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "a"),),
        send_to="your partner",
        send_line="It's a big hour.",
    ),
    style="Stick",
    parts={},
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
