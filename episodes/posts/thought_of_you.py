"""The release of thought-of-you."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "thought-of-you",
    InstagramPost(
        title="What did your mom forward you this week?",
        description=(
            "She found an article. She has no comment. It is about you.\nA Collage sketch on Okayville, voiced with"
            " ElevenLabs premade voices Chris (Gary) and Matilda (Rosa); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris and Matilda. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#mom", "#family", "#momlife", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Mom sent another link", 8.2, focus=(540.0, 1100.0), zoom=1.15, number=199),
    ),
    tags=Tags(
        "everyday-tech",
        "other-person",
        "embarrassment",
        recurring=("gary", "rosa"),
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "a"),),
        send_to="your mom",
        send_line="Saw it and thought of you.",
    ),
    style="Collage",
    parts={
        "collage-alarm-clock": 1,
        "collage-arm": 1,
        "collage-bedroom": 1,
        "collage-duvet": 1,
        "collage-gary": 1,
        "collage-living-room": 1,
        "collage-phone": 1,
        "collage-rosa": 1,
        "collage-sign": 1,
        "collage-sofa": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=18, reviewer=18),
    cover=True,
)
