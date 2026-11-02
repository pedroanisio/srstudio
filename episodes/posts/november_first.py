"""The release of november-first."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "november-first",
    InstagramPost(
        title="When does Christmas start in your house?",
        description=(
            "She decorated overnight. The pumpkin has been told. So has the speaker.\nA Stick sketch on Okayville, "
            "voiced with ElevenLabs premade voices Will (Dev), Jessica (Noor) and Alice (the speaker); every "
            "character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will, Jessica and Alice. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#christmas", "#couples", "#marriage", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("The morning after\nHalloween", 2.15, number=210),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "affection",
        recurring=("dev", "noor"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "b"),),
        send_to="your partner",
        send_line="Who?",
    ),
    style="Stick",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-kitchen": 1,
        "stick-mug": 1,
        "stick-rig": 1,
        "stick-robe": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=16, reviewer=15),
    cover=True,
)
