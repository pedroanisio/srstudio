"""The release of your-half."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "your-half",
    InstagramPost(
        title="What's the smallest thing a roommate ever billed you for? Saga #19",
        description=(
            "Under fire, Rook sends Juno a payment request for half a ration bar. Then the missile hits her side.\n"
            "A Saga sketch on Okayville, a space-opera parody voiced with ElevenLabs premade voices George "
            "(narrator), Roger (Rook) and River (Juno); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Roger and River. Sound effects generated with ElevenLabs. "
            "Original characters, drawn in code."
        ),
        hashtags=("#roommates", "#splitthebill", "#spaceopera", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Your half", 6.0, number=208, series="Saga", series_number=19),
    ),
    tags=Tags(
        "epic-world",
        "other-person",
        "recognition",
        recurring=("rook", "juno"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "a"),),
        send_to="your roommate",
        send_line="You rounded down.",
    ),
    style="Saga",
    parts={
        "saga-cockpit": 1,
        "saga-cockpit-console": 1,
        "saga-fighter": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-juno": 1,
        "saga-rook": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)
