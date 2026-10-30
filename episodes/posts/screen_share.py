"""The release of screen-share."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "screen-share",
    InstagramPost(
        title="Can everyone see my screen?",
        description=(
            "Yes. And the inbox. All of it. Three beats of a remote workday: a shared screen that shows too much, a "
            "meeting that runs over meets a very bad connection, and a Friday 4:59 PM \"got a sec?\".\n"
            "Stick 02, the first original episode in the Stick style: drawn stick figures, a call screen and a boss "
            "who walks in."
        ),
        credit="Voices: ElevenLabs premade voices Eric and Will. Sound effect generated with ElevenLabs.",
        hashtags=(
            "#screenshare",
            "#remotework",
            "#zoommeeting",
            "#officehumor",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
        ),
        thumbnail=Thumbnail("Can everyone\nsee my screen?", 2.2, "Stick 02", (380, 900), 2.2),
    ),
    characters={"stick-rig": 1},
)
