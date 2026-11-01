"""The release of whats-new."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "whats-new",
    InstagramPost(
        title="Why did they move it?",
        description=(
            "Every update moves the one thing you use and calls it an improvement. This one is a man in your "
            "house, and he has moved the sofa.\nA Soft sketch on Okayville, voiced with ElevenLabs premade voices "
            "Laura (Juno), Alice (Pip) and Eric (Bo); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Laura, Alice and Eric. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#softwareupdate', '#techhumor', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("We improved your living room", 6.9, number=195),
    ),
    tags=Tags(
        "everyday-tech", "institution", "recognition", recurring=('bo', 'juno', 'pip'), test="sp-speakers", arm="b"
    ),
    style="Soft",
    parts={},
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
