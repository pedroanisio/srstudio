"""The release of i-was-watching."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "i-was-watching",
    InstagramPost(
        title="He is not asleep. He was watching that.",
        description=(
            "Bruno has been asleep since the opening credits. Mae turns the movie off. He was watching that. She "
            "keeps clicking.\n"
            "A Toon sketch with Bruno and Mae, voiced with ElevenLabs premade voices Bill, Sarah and Roger; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Bill (Bruno), Sarah (Mae) and Roger (the buyer). Foley synthesised.",
        hashtags=("#couples", "#relationshiphumor", "#movienight", "#animatedshorts", "#comedyshorts", "#cartoon"),
        thumbnail=Thumbnail("He was\nwatching that.", 19.8, "Toon 28", (500, 1000), 1.2),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "affection",
        recurring=("bruno", "mae"),
        test="sp-hook_motion",
        arm="a",
        recipient="b",
        to="partner",
    ),
    style="toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-badge": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-goat": 1,
        "toon-lounge": 1,
        "toon-rabbit": 2,
        "toon-speaker": 1,
    },
)
