"""The release of sorry-what."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "sorry-what",
    InstagramPost(
        title="What did you just agree to?",
        description=(
            "You get two sorrys. Everyone knows this. After that you are a person who"
            " has a horse.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Chris (Gil), Roger "
            "(the neighbor) and Jessica (across the road); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris, Roger and Jessica. Original characters, drawn in code. "
            "Sound effects synthesized in code."
        ),
        hashtags=('#neighbors', '#awkward', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("You only\nget two.", 7.0, "Okayville"),
    ),
    tags=Tags("own-worst-enemy", "protagonist", "tension", recurring=('gil', 'keith'), test="sp-hook_motion", arm="b"),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-blower": 1,
        "toon-captions": 1,
        "toon-frog": 2,
        "toon-hallway": 1,
        "toon-hamster": 1,
        "toon-hedgehog": 2,
        "toon-horse": 1,
        "toon-key-line": 1,
        "toon-ledge": 1,
        "toon-mower": 1,
        "toon-scribble": 1,
        "toon-side-car": 1,
        "toon-sloth": 1,
        "toon-yard": 1,
    },
    comedy=Scores(author=16, reviewer=18),
)
