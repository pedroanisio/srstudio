"""The release of it-autoplayed."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "it-autoplayed",
    InstagramPost(
        title="Which one of you can't wait for the other?",
        description=(
            "Two episodes in, together. He gasped before the door.\nA Toon sketch on Okayville, voiced with ElevenLabs "
            "premade voices Sarah (Mae) and Bill (Bruno); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah and Bill. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#couples", "#tvshows", "#spoilers", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("He gasped before the door", 23.3, number=202),
    ),
    tags=Tags(
        "everyday-tech",
        "other-person",
        "embarrassment",
        recurring=("mae", "bruno"),
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "a"),),
        send_to="your partner",
        send_line="It autoplayed.",
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
        "toon-sofa": 1,
        "toon-sofa-back": 1,
        "toon-speaker": 1,
        "toon-swung-arm": 1,
    },
    comedy=Scores(author=18, reviewer=18),
    cover=True,
)
