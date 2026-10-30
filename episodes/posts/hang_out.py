"""The release of hang-out."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "hang-out",
    InstagramPost(
        title="We have to catch up",
        description=(
            "Two best friends, one calendar each, and a shared belief that this week is the crazy one.\n"
            "Juno and Pip, and a tree that gets on with it."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno) and Will (Pip). Foley synthesised.",
        hashtags=(
            "#friendship",
            "#bestfriends",
            "#adulting",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("We HAVE to\ncatch up!", 1.0, place="top"),
    ),
    style="Soft",
    # soft-bench, soft-cane, soft-park, soft-phone and soft-time-card join these at version 1 once the operator decides
    # them: a release cannot pin a proposed version, so until then the delivery pin check refuses this reel.
    parts={"captions": 1, "juno": 1, "pip": 1, "signature-cactus": 1, "signature-code": 1},
    tags=Tags(
        territory="relationships",
        cause="protagonist",
        emotion="affection",
        recurring=("pip", "juno"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="best friend",
    ),
)
