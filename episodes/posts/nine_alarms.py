"""The release of nine-alarms."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "nine-alarms",
    InstagramPost(
        title="Who hears the alarm in your house?",
        description=(
            "One person in every bed sets nine alarms, sleeps through all of them and wakes up rested. The other "
            "one hears every single one.\nA Toon sketch on Okayville, voiced with ElevenLabs premade voices Sarah "
            "(Mae), Bill (Bruno) and Alice (the phone); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Sarah, Bill and Alice. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#alarmclock', '#couplehumor', '#morningpeople', '#animatedshorts', '#okayville'),
        thumbnail=ShowCover("Alarm 1 of 9", 5.3, number=194),
    ),
    tags=Tags(
        "everyday-tech",
        "other-person",
        "recognition",
        recurring=("bruno", "mae"),
        test="sp-speakers",
        arm="b",
        send_to="your partner",
        send_line="Babe. My alarm didn't go off.",
    ),
    style="Toon",
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 2,
        "toon-captions": 1,
        "toon-key-line": 1,
        "toon-phone": 1,
        "toon-rabbit": 2,
    },
    comedy=Scores(author=18, reviewer=18),
    cover=True,
)
