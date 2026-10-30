"""The release of the-router."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-router",
    InstagramPost(
        title="Have you tried turning me off and on again?",
        description=(
            "The internet is down and the router knows exactly how to fix it. It just would rather you did it.\n"
            "Ink 02: the second square cartoon, an original talking appliance this time."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#routerproblems",
            "#officehumor",
            "#itsupport",
            "#turnitoffandonagain",
            "#handdrawn",
            "#animatedshorts",
            "#workcomedy",
        ),
        thumbnail=Thumbnail("Off and\non again?", 11.0, "Ink 02", place="top"),
    ),
    parts={
        "doodle": 1,
        "ink-closeup": 1,
        "ink-desk": 1,
        "ink-desk-shot": 1,
        "ink-hand": 1,
        "ink-laptop": 1,
        "ink-router-shot": 1,
        "ink-router-wide": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "talking-router": 1,
    },
)
