"""The release of arrive-early."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "arrive-early",
    InstagramPost(
        title="Cash or card?",
        description=(
            "Your appointment was at nine?\n"
            "A Toon sketch voiced with ElevenLabs premade voices Matilda (the patient), Will (the receptionist) and "
            "Charlie (the doctor); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Matilda, Will and Charlie. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#doctor", "#waitingroom", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("Take a seat.", 17.0, "Toon"),
    ),
    tags=Tags("money-services", "institution", "triumph", test="sp-hook_motion", arm="b"),
    style="Toon",
    comedy=Scores(author=17, reviewer=17),
    parts={
        # toon-reception-glass is drawn too; it stays out until it is approved: a release cannot pin a proposed version.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-card-reader": 1,
        "toon-clipboard": 1,
        "toon-clock": 1,
        "toon-counter": 1,
        "toon-dog": 2,
        "toon-frog": 2,
        "toon-hall-chair": 1,
        "toon-hallway": 1,
        "toon-ledge": 1,
        "toon-raccoon": 2,
    },
)
