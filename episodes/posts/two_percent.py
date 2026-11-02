"""The release of two-percent."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "two-percent",
    InstagramPost(
        title="Who's always on 2% in your group?",
        description=(
            "She never charges. He never says no.\nA Soft sketch on Okayville, voiced with ElevenLabs premade voices"
            " Laura (Juno) and Will (Pip); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Laura and Will. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#battery", "#bestfriend", "#nightout", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Always on 2%", 14.0, number=211),
    ),
    tags=Tags(
        "everyday-tech",
        "other-person",
        "recognition",
        recurring=("juno", "pip"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "a"),),
        send_to="your best friend",
        send_line="You should really charge your phone.",
    ),
    style="Soft",
    video="two-percent-v2",  # the keeper: the first master ran the caption outlines across the spaces between words
    parts={
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-battery-screen": 1,
        "soft-bench": 1,
        "soft-park": 1,
        "soft-phone": 1,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
