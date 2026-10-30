"""The release of off-and-on."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "off-and-on",
    InstagramPost(
        title="IT support has one fix. It's a jingle.",
        description=(
            "The coffee machine is broken: turn it off and on again. Pip is broken: lights off, lights on, and now "
            "he loves Mondays. Then Remy's own screen dies, and the IT hotline knows exactly what to say.\n"
            "Episode 10, the third in the Soft style, with Juno and Remy in the new meeting room and break room."
        ),
        credit=(
            "Music and Remy's vocal composed with the ElevenLabs Music API. Voices: ElevenLabs premade voices Laura "
            "(Juno), Will (Pip) and Charlie (IT hotline). Sound effects generated with ElevenLabs."
        ),
        hashtags=(
            "#itsupport",
            "#turnitoffandonagain",
            "#mondays",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Somebody\nreboot me.", 29.5, "Episode 10", (600, 1000), 1.2),
    ),
    characters={"juno": 1, "pip": 1, "remy": 1},
)
