"""The release of not-a-robot."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "not-a-robot",
    InstagramPost(
        title="One form before lunch. How hard can it be?",
        description=(
            "Select all traffic lights. Select all traffic lights that are sad. Select every moment you felt truly "
            "alive. He hesitated like a human and clicked like a robot, and the router from The Router welcomes its "
            "brother home.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris, Sarah and Daniel."
        ),
        credit="Voices: ElevenLabs premade voices Chris, Sarah and Daniel. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#captcha",
            "#imnotarobot",
            "#techhumor",
            "#officehumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Prove you're\nnot a robot.", 15.0, "Ink 03", place="top"),
    ),
    cover=True,
)
