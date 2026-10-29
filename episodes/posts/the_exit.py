"""The release of the-exit."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-exit",
    InstagramPost(
        title="You missed the exit.",
        description=(
            "Your sister's wedding. Your mum's birthday. The tent. Some couples have had the same argument so many "
            "times they can run the whole thing in four words, and then find out where they are no longer going.\n"
            "Stick 09: Dev and Noor through the windshield, a car drawn in code with the road behind them, the "
            "captions one word at a time."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Jessica. Sound effects and instrumental music composed with "
            "ElevenLabs."
        ),
        hashtags=(
            "#couplegoals",
            "#relationshiphumor",
            "#roadtrip",
            "#marriedlife",
            "#inlaws",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("You missed\nthe exit.", 6.8, "Stick 09", (540, 820), 1.15, place="top"),
    ),
    cover=True,
    tags=Tags("relationships", "protagonist", "affection", recurring=("dev", "noor")),
)
