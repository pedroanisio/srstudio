"""The release of thought-of-you."""

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
        thumbnail=ShowCover("Mom sent another link", 3.9, number=199),
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
    parts={},
    cover=True,
)
