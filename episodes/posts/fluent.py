"""The release of fluent."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "fluent",
    InstagramPost(
        title="Is your CV as fluent as you are?",
        description=(
            "Her CV says French. So does his. Between them they have one pastry.\nA Collage sketch on "
            "Okayville, voiced with ElevenLabs premade voices Brian (Brent) and Jessica (Deb); every character is"
            " original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian and Jessica. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobinterview', '#resume', '#learnfrench', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Fluent\nin French?", 12.4, "Okayville"),
    ),
    tags=Tags(
        "job-hunting", "protagonist", "embarrassment", recurring=('brent', 'deb'), test="sp-hook_motion", arm="b"
    ),
    style="Collage",
    parts={
        "collage-arm": 1,
        "collage-boardroom": 1,
        "collage-brent": 1,
        "collage-counter": 1,
        "collage-deb": 1,
        "collage-desk-phone": 1,
        "collage-eye-twitch": 1,
        "collage-handset": 1,
        "collage-resume": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=16, reviewer=19),
)
