"""The release of only-your-aunt."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "only-your-aunt",
    InstagramPost(
        title="Who did your mom tell?",
        description=(
            "One interview, and the whole town wished him luck.\nA Cutout sketch on Okayville, voiced with "
            "ElevenLabs premade voices Liam (Milo) and Lily (Rosa); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Liam and Lily. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#mom', '#jobinterview', '#family', '#relatable', '#okayville'),
        thumbnail=ShowCover("Don't tell anyone", 3.4, number=193),
    ),
    tags=Tags(
        "job-hunting",
        "other-person",
        "embarrassment",
        test="sp-speakers",
        arm="a",
        send_to="your mom",
        send_line="Nobody! Your aunt doesn't count.",
    ),
    style="Cutout",
    parts={
        "barista": 1,
        "bean-jar": 1,
        "bench": 1,
        "building": 1,
        "cafe": 1,
        "cafe-window": 1,
        "cake-knife": 1,
        "cake-slice": 1,
        "candidate": 1,
        "captions": 1,
        "coffee-cup": 1,
        "crayon-page": 1,
        "customer": 1,
        "espresso-machine": 1,
        "globe-pendant": 1,
        "held-phone": 1,
        "home-study": 1,
        "lettered-cup": 1,
        "manager": 1,
        "menu-board": 1,
        "paper-streamers": 1,
        "papers": 1,
        "park": 1,
        "park-sign": 1,
        "pastry-stand": 1,
        "pendant-light": 1,
        "pigeon": 1,
        "reaching-hand": 1,
        "reception": 1,
        "reception-counter": 1,
        "rosa": 1,
        "sheet-cake": 1,
        "show-bug": 1,
        "shrub": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "slat-wall": 1,
        "tree": 1,
    },
    comedy=Scores(author=17, reviewer=18),
    cover=True,
)
