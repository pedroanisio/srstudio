"""The release of repeat-after-me."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "repeat-after-me",
    InstagramPost(
        title="Repeat after me.",
        description=(
            "I will not check my email on the drive home. I will leave work at work. Say it twice, say it firmer, "
            "and whatever you do, don't look at the passenger seat.\n"
            "Stick 03: Dev's vows on the commute, a car drawn in code with the road passing in the window, and the "
            "captions one word at a time."
        ),
        credit="Voice: ElevenLabs premade voice Will. Sound effect and instrumental music composed with ElevenLabs.",
        hashtags=(
            "#workfromcar",
            "#worklifebalance",
            "#afterhours",
            "#officehumor",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Repeat\nafter me.", 10.8, "Stick 03", (540, 1200), 1.3),
    ),
    cover=True,
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "stick-car": 1,
        "stick-car-seat": 1,
        "stick-card": 1,
        "stick-cockpit": 1,
        "stick-laptop": 1,
        "stick-phone": 1,
        "stick-ride": 1,
        "stick-rig": 1,
        "stick-words": 1,
    },
)
