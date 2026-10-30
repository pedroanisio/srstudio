"""The release of check-with-my-team."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "check-with-my-team",
    InstagramPost(
        title="POV: you gotta check with your team first.",
        description=(
            "Let me just check with my team real quick and get back to you. The team turns out to be one person and "
            "three AI assistants, dancing in a garden. Three hours later, the verdict is in.\n"
            "Recreation of @theaifilmmaker's cartoon in the Stick style: traced stick figures on painted sets, "
            "outlined captions, a new synthesised voice-over and music at the dance's tempo. Character art, dialogue "
            "and lettering are adapted from the reference, and the original creator retains rights; the card and the "
            "closing line are new."
        ),
        credit="Voice-over: ElevenLabs premade voice Chris. Music composed with ElevenLabs Music. "
        "Reference: @theaifilmmaker.",
        hashtags=(
            "#checkwithmyteam",
            "#officehumor",
            "#aitools",
            "#workcomedy",
            "#stickfigure",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Let me check\nwith my team", 0.8, "POV", (430, 900), 1.3),
    ),
    scene="scene.xml",
    cover=True,
    characters={"stick-figure": 1},
)
