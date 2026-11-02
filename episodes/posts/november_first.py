"""The release of november-first."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "november-first",
    InstagramPost(
        title="When does Christmas start in your house?",
        description=(
            "She decorated overnight. The pumpkin has been told. So has the speaker.\nA Stick sketch on Okayville, "
            "voiced with ElevenLabs premade voices Will (Dev) and Jessica (Noor); every character is original, drawn "
            "in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Jessica. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#christmas", "#couples", "#marriage", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("The morning after\nHalloween", 2.15, number=210),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "affection",
        recurring=("dev", "noor"),
        test="sp-length",
        arm="short",
        # Excluded from sp-speakers: drawn arm b (about 3 speaking), but the speaker's voice was dropped under the canon
        # rule systems-answer-in-notifications (it answers by a chip), which leaves 2 speaking voices. Neither arm is
        # claimed: relabelling it arm a would put a reel the draw did not assign into that arm.
        send_to="your partner",
        send_line="Who?",
    ),
    style="Stick",
    video="november-first-v2",  # the keeper: the first master had the speaker speak and lost "Who?"'s question mark
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-holiday-tree": 1,
        "stick-kitchen": 1,
        "stick-light-string": 1,
        "stick-mug": 1,
        "stick-pumpkin": 1,
        "stick-rig": 1,
        "stick-robe": 1,
        "stick-smart-speaker": 1,
        "stick-step-stool": 1,
        "stick-tree-star": 1,
        "stick-words": 1,
        "stick-worktop": 1,
    },
    comedy=Scores(author=16, reviewer=15),
    cover=True,
)
