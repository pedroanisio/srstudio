"""The release of the-profiles."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-profiles",
    InstagramPost(
        title="Is your ex still on your streaming account?",
        description=(
            "Three years. They finally met to end it. There was one "
            "thing neither of them saw coming.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices "
            "River (Mia) and Roger (Brock); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices River and Roger. Original characters, drawn in code. Sound effects"
            " synthesized in code."
        ),
        hashtags=('#exes', '#streaming', '#breakups', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("We were\nsaving that.", 21.8, "Okayville"),
    ),
    tags=Tags(
        "relationships", "other-person", "recognition", recurring=('mia', 'brock'), test="sp-hook_motion", arm="a"
    ),
    style="Toon",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-device-list": 1,
        "toon-dog": 2,
        "toon-hamster": 1,
        "toon-ledge": 1,
        "toon-phone": 1,
        "toon-profile-list": 1,
        "toon-rabbit": 2,
        "toon-restaurant": 1,
        "toon-table": 1,
    },
    comedy=Scores(author=15, reviewer=17),
)
