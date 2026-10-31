"""The release of wave-back."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "wave-back",
    InstagramPost(
        title="Ever waved back at someone who wasn't waving at you?",
        description=(
            "Your arm is up now. It lives there. Make something of it."
            "\n"
            "A Stick sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Jessica (Noor), Callum (the man) and Lily (the passer-by). "
            "Foley synthesized."
        ),
        hashtags=('#awkward', '#wavingback', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("Stretching.\nJust stretching.", 7.9, "Stick 20"),
    ),
    cover=True,
    tags=Tags(
        "own-worst-enemy",
        "protagonist",
        "embarrassment",
        recurring=("noor",),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="best friend",
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-gym": 1,
        "stick-gym-counter": 1,
        "stick-rig": 1,
        "stick-street-lens": 1,
        "stick-words": 1,
    },
    comedy=Scores(16, 19),
)
