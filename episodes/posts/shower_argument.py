"""The release of shower-argument."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "shower-argument",
    InstagramPost(
        title="Have you ever lost an argument in the shower?",
        description=(
            "Three days late, Rex finally has the perfect comeback."
            " So does she.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Charlie (Rex), "
            "Matilda (Fern) and River (Mia); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Charlie, Matilda and River. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#showerthoughts', '#overthinking', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Did you\nwin?", 17.0, "Okayville"),
    ),
    tags=Tags(
        "own-worst-enemy",
        "protagonist",
        "recognition",
        recurring=('rex', 'fern', 'mia'),
        test="sp-hook_motion",
        arm="b",
    ),
    style="Toon",
    parts={
        # toon-bathroom, toon-shower-water also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dog": 2,
        "toon-frog": 2,
        "toon-ledge": 1,
        "toon-shampoo": 1,
    },
    comedy=Scores(author=16, reviewer=17),
)
