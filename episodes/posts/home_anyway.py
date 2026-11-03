"""The release of home-anyway."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "home-anyway",
    InstagramPost(
        title="What does your partner think you do all day?",
        description=(
            "He's looking for a job. She thinks he's home, and home is where the plumber goes.\nA Toon sketch on "
            "Okayville, voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno); every character is "
            "original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah and Bill. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#jobhunting", "#couplehumor", "#unemployedlife", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Day 41, one bare corner", 19.1, number=198),
    ),
    tags=Tags(
        "job-hunting",
        "other-person",
        "tension",
        recurring=("bruno", "mae"),
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "a"),),
        send_to="your partner",
        send_line="Can you move it? You're home anyway.",
    ),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-hallway": 1,
        "toon-key-line": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-open-laptop": 1,
        "toon-rabbit": 2,
        "toon-swung-arm": 1,
    },
    comedy=Scores(author=18, reviewer=17),
    cover=True,
)
