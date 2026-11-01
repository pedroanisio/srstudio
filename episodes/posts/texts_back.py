"""The release of texts-back."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "texts-back",
    InstagramPost(
        title="Did the recruiter ever text back?",
        description=(
            "Dana has read every man who ever went quiet on Mia. Now she reads the recruiter.\nA Toon sketch on "
            "Okayville, voiced with ElevenLabs premade voices River (Mia) and Jessica (Dana); every character is "
            "original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices River and Jessica. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#jobhunting", "#bestfriends", "#recruiters", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Eleven days. No reply.", 16.6, number=200),
    ),
    tags=Tags(
        "job-hunting",
        "institution",
        "triumph",
        recurring=("dana", "mia"),
        test="sp-length",
        arm="natural",
        also=(("sp-speakers", "a"),),
        send_to="your best friend",
        send_line="You deserve a company that texts back.",
    ),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-dog": 2,
        "toon-key-line": 1,
        "toon-lounge": 1,
        "toon-mug": 1,
        "toon-phone": 1,
        "toon-rabbit": 2,
        "toon-sofa": 1,
        "toon-sofa-back": 1,
        "toon-speaker": 1,
        "toon-swung-arm": 1,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
