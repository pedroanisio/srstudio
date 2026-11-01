"""The release of cant-afford-to-save."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "cant-afford-to-save",
    InstagramPost(
        title="Who in your house saves like this?",
        description=(
            "Sixty percent off. Four thousand dollars saved. One bank account, looking at it.\nA Stick sketch on "
            "Okayville, voiced with ElevenLabs premade voices Will (Dev) and Jessica (Noor); every character is "
            "original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Jessica. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#blackfriday', '#couples', '#money', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Black Friday at home", 10.5, number=201),
    ),
    tags=Tags(
        "money-services",
        "protagonist",
        "recognition",
        recurring=("dev", "noor"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "a"),),
        send_to="your partner",
        send_line="We can't afford to save any more.",
    ),
    style="Stick",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-box": 1,
        "stick-card": 1,
        "stick-handset": 1,
        "stick-receipt": 1,
        "stick-rig": 1,
        "stick-room": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
