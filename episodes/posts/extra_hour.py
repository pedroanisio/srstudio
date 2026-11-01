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
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-chair": 1,
        "stick-handset": 1,
        "stick-key": 1,
        "stick-kitchen": 1,
        "stick-mug": 1,
        "stick-plate": 1,
        "stick-rig": 1,
        "stick-table": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
