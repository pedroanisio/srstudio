"""The release of left-at-door."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "left-at-door",
    InstagramPost(
        title="I don't own a gnome.",
        description=(
            "Whose door is that?\n"
            "A Toon sketch voiced with ElevenLabs premade voices Brian (the narrator) and Matilda (the neighbor); "
            "every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Matilda. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#delivery", "#noodles", "#relatable", "#animatedshorts", "#comedy"),
        thumbnail=Thumbnail("One gnome.", 5.0, "Toon"),
    ),
    tags=Tags("everyday-tech", "institution", "embarrassment", test="sp-hook_motion", arm="b"),
    style="Toon",
    comedy=Scores(author=17, reviewer=16),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-frog": 2,
        "toon-gnome": 1,
        "toon-ledge": 1,
        "toon-night-street": 1,
        "toon-noodle-box": 1,
        "toon-phone": 1,
        "toon-porch": 1,
        "toon-rain": 1,
        "toon-side-car": 1,
        "toon-sloth": 1,
    },
)
