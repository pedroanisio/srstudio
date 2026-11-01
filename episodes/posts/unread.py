"""The release of unread."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "unread",
    InstagramPost(
        title="Who do you know with 41,000 unread?",
        description=(
            "Pip's rule is simple: if it's important, they'll call. His car, his lease and his new job would like a "
            "word.\nA Soft sketch on Okayville, voiced with ElevenLabs premade voices Laura (Juno) and Will (Pip); "
            "every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Laura and Will. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#email", "#inbox", "#relatable", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("41,000 unread", 2.6, number=206),
    ),
    tags=Tags(
        "everyday-tech",
        "protagonist",
        "recognition",
        recurring=("juno", "pip"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "a"),),
        send_to="your friend with the unread emails",
        send_line="If it's important, they'll email.",
    ),
    style="Soft",
    parts={
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-bench": 1,
        "soft-call-screen": 1,
        "soft-mail-list": 1,
        "soft-mail-screen": 1,
        "soft-notice": 1,
        "soft-park": 1,
        "soft-phone": 1,
    },
    comedy=Scores(author=18, reviewer=17),
    cover=True,
)
