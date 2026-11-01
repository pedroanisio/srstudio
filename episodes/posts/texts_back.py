"""The release of texts-back."""

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
    parts={},
    cover=True,
)
