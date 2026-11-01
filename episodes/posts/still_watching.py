"""The release of still-watching."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "still-watching",
    InstagramPost(
        title="When did your TV last ask how you are?",
        description=(
            "It only wants what's best for him. Then it counts to five.\nA Soft sketch on Okayville, voiced with "
            "ElevenLabs premade voices Eric (Bo) and Alice (the television); every character is original, drawn "
            "in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Eric and Alice. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#streaming', '#bingewatching', '#relatable', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("It's four a.m.", 7.0, number=196),
    ),
    tags=Tags("everyday-tech", "protagonist", "affection", test="sp-speakers", arm="a"),
    style="Soft",
    parts={"bo": 1, "captions": 1, "show-bug": 1, "signature-cactus": 1, "signature-code": 1, "soft-time-card": 1},
    comedy=Scores(author=16, reviewer=17),
    cover=True,
)
