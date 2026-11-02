"""The release of grown-on-me."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "grown-on-me",
    InstagramPost(
        title="Which one of you said it first?",
        description=(
            "Forty-five minutes of picking a movie. He found one he likes.\nA clay sketch on Okayville, voiced with "
            "ElevenLabs premade voices Sarah (Mae), Bill (Bruno) and Brian (the trailer); every character is "
            "original, made in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah, Bill and Brian. Original characters, made in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#couples", "#movienight", "#claymation", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("It's grown on me", 28.6, number=213),
    ),
    tags=Tags(
        "everyday-tech",
        "other-person",
        "recognition",
        recurring=("mae", "bruno"),
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "b"),),
        send_to="your partner",
        send_line="That's the first one I said.",
    ),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-key-line": 1,
        "toon-lounge": 1,
        "toon-rabbit": 2,
        "toon-sofa-back": 1,
        "toon-speaker": 1,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
