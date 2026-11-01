"""The release of store-credit."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "store-credit",
    InstagramPost(
        title="Can you return a battle station? Saga #20",
        description=(
            "However badly the thing exploded, the desk has a policy, and the policy is a coupon.\nA Saga sketch "
            "on Okayville, voiced with ElevenLabs premade voices Callum (Lord Gloom), Jessica (the droid), Liam "
            "(Enforcer Seven) and George (the narrator); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Callum, Jessica, Liam and George. Original characters, drawn in "
            "code. Sound effects synthesized in code."
        ),
        hashtags=('#spaceopera', '#customerservice', '#refund', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Expires today", 27.2, number=215, series="Saga", series_number=20),
    ),
    tags=Tags("epic-world", "institution", "recognition", test="sp-speakers", arm="b"),
    style="Saga",
    parts={
        "saga-droid": 1,
        "saga-enforcer": 1,
        "saga-entry": 1,
        "saga-gloom": 1,
        "saga-handbook": 1,
        "saga-hook": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=15, reviewer=15),
    cover=True,
)
