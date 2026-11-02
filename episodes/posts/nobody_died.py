"""The release of nobody-died."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "nobody-died",
    InstagramPost(
        title='Why does "don\'t worry" make it worse?',
        description=(
            "Final interview. Nine missed calls. One lamp.\nA Cutout sketch on Okayville, voiced with ElevenLabs "
            "premade voices Liam (Milo), Lily (Rosa) and Eric (the manager); every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam, Lily and Eric. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#mom", "#jobinterview", "#family", "#relatable", "#okayville"),
        thumbnail=ShowCover("Nine missed calls", 21.0, number=203),
    ),
    tags=Tags(
        "job-hunting",
        "other-person",
        "tension",
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "b"),),
        send_to="your mom",
        send_line="Nobody died. Do you want a lamp?",
    ),
    style="Cutout",
    parts={
        "back-room": 1,
        "captions": 1,
        "customer": 1,
        "desk-phone": 1,
        "held-phone": 1,
        "home-study": 1,
        "laptop": 1,
        "manager": 1,
        "papers": 1,
        "reaching-hand": 1,
        "rosa": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "table-lamp": 1,
        "table-phone": 1,
        "video-tile": 1,
    },
    comedy=Scores(author=18, reviewer=17),
    cover=True,
)
