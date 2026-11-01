"""The release of third-snore."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "third-snore",
    InstagramPost(
        title="Do you snore, or is it the other one?",
        description=(
            "Each swears it is the other one. So she recorded it. There is a reason you should not check.\n"
            "A Stick sketch on Okayville, voiced with ElevenLabs premade voices Jessica (Noor), Will (Dev) and Callum "
            "(Gary); every character is original, drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Jessica, Will and Callum. Original characters, drawn in code. Sound "
        "effects with ElevenLabs.",
        hashtags=("#snoring", "#marriagehumor", "#relationships", "#stickfigure", "#okayville"),
        thumbnail=Thumbnail("Whose snore\nis that?", 11.5, "Okayville", (540, 860), 1.0, place="bottom"),
    ),
    cover=True,
    tags=Tags(
        "relationships", "other-person", "tension", recurring=("dev", "noor", "gary"), test="sp-hook_motion", arm="b"
    ),
    style="Stick",
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-card": 1,
        "stick-duvet": 1,
        "stick-eye-mask": 1,
        "stick-lights-low": 1,
        "stick-murphy-bed": 1,
        "stick-recorder": 1,
        "stick-rig": 1,
        "stick-studio-flat": 1,
        "stick-words": 1,
    },
    comedy=Scores(author=16, reviewer=19),
)
