"""The release of one-symptom."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "one-symptom",
    InstagramPost(
        title="Why did you look it up?",
        description=(
            "Never look up one symptom. Never read one out loud."
            "\n"
            "A Toon sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Callum (the patient) and Brian (the doctor). Foley synthesised.",
        hashtags=('#webmd', '#doctor', '#relatable', '#animatedshorts', '#comedyshorts'),
        thumbnail=Thumbnail("You have a headache.", 3.4, "Toon 33"),
    ),
    tags=Tags("own-worst-enemy", "protagonist", "tension", test="sp-hook_motion", arm="a", recipient="a"),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-finger": 1,
        "toon-hedgehog": 2,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-phone": 1,
        "toon-sloth": 1,
        "toon-surgery": 1,
    },
    comedy=Scores(17, 19),
)
