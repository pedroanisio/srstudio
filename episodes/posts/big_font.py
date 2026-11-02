"""The release of big-font."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "big-font",
    InstagramPost(
        title="What size is your mom's font?",
        description=(
            "She can't read yours. She read yours.\nA Collage sketch on Okayville, voiced with ElevenLabs premade "
            "voices Matilda (Rosa) and Chris (Gary); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda and Chris. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#mom", "#family", "#texting", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Mom texts in giant font", 0.6, number=209),
    ),
    tags=Tags(
        "family",
        "other-person",
        "recognition",
        recurring=("rosa", "gary"),
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "a"),),
        send_to="your mom",
        send_line="Tell your brother I can read that.",
    ),
    style="Collage",
    parts={
        "collage-arm": 1,
        "collage-bubble": 1,
        "collage-dining-room": 1,
        "collage-food": 1,
        "collage-gary": 1,
        "collage-phone": 1,
        "collage-rosa": 1,
        "collage-tablecloth": 1,
        "collage-thread": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=18, reviewer=16),
    cover=True,
)
